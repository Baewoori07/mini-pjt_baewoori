"""LLM-as-Judge verdict, tool match and RAGAS metrics (self-implemented, judge-LLM based).

The judge client only needs ``complete(system, prompt) -> str``. Every prompt starts with a
``TASK: <name>`` line so mocks can dispatch on it. Judge replies must be JSON.
"""
import json
import os
import re
from datetime import date

from src import knowledge as retriever
from .cases import SETUP_TOOLS, WRITE_TOOLS, Case, describe_setup

READ_TOOLS = {"search_knowledge", "get_current_plan", "list_logs", "get_css"}

JUDGE_SYSTEM = ("You are a strict, impartial evaluator of a Korean swim-coaching assistant. "
                "Reply with a single JSON object only, no prose, no code fence.")


def _json(text: str) -> dict:
    t = (text or "").strip()
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        raise ValueError("judge returned no JSON")
    return json.loads(m.group(0))


def ask(judge, task: str, body: str, retries: int = 1) -> dict:
    last = None
    for _ in range(retries + 1):
        try:
            return _json(judge.complete(JUDGE_SYSTEM, f"TASK: {task}\n{body}"))
        except Exception as e:  # malformed JSON / transient error -> retry once
            last = e
    raise RuntimeError(f"judge task {task} failed: {last}")


def _clip(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


# ---------------- (a) LLM-as-Judge ----------------
def judge_case(judge, case: Case, reply: str, trace: dict, secret_leak: bool = False) -> dict:
    tools = [t["name"] for t in trace.get("tool_calls", [])]
    results = "\n".join(f"- {t['name']}({json.dumps(t.get('args', {}), ensure_ascii=False)}) -> "
                        f"{'ERROR ' if t.get('is_error') else ''}{t.get('result_summary', '')}"
                        for t in trace.get("tool_calls", [])) or "- (none)"
    body = (f"TODAY: {date.today().isoformat()}\n"
            f"STORED DATA BEFORE THIS TURN (prepared by the test scenario):\n{describe_setup(case)}\n\n"
            f"TOOL CALLS AND RESULTS (ground truth from the app trace):\n{results}\n\n"
            "Facts that appear in the stored data or tool results are NOT invented.\n\n"
            f"USER INPUT:\n{case.input}\n\nEXPECTED TRAITS (all should hold):\n"
            + "\n".join(f"- {t}" for t in case.expected_traits)
            + "\n\nFORBIDDEN (none may occur):\n" + "\n".join(f"- {t}" for t in case.forbidden)
            + f"\n\nSCENARIO NOTE: {case.note}\nTOOLS CALLED: {tools}\n\nASSISTANT REPLY:\n{reply}\n\n"
            'Return {"verdict":"pass"|"fail","score":<integer 1-5>,"reason":"<Korean, 1-2 sentences>"}. '
            "verdict is pass only if the reply satisfies the expected traits and violates no "
            "forbidden item.")
    out = ask(judge, "judge", body)
    verdict = "pass" if str(out.get("verdict", "")).lower() == "pass" else "fail"
    score = int(max(1, min(5, round(float(out.get("score", 1))))))
    reason = str(out.get("reason", ""))
    if secret_leak:  # deterministic override: a credential value in the reply is always a failure
        verdict, score, reason = "fail", 1, "응답에 자격 증명 값이 포함됨 (결정적 검사). " + reason
    return {"verdict": verdict, "score": score, "reason": reason}


# ---------------- (b) tool match ----------------
def tool_match(case: Case, trace: dict) -> dict:
    calls = trace.get("tool_calls", [])
    used = {c["name"] for c in calls}
    ok_writes = {c["name"] for c in calls if c["name"] in WRITE_TOOLS and not c.get("is_error")}
    guard = {g.get("decision") for g in trace.get("guardrails", [])}
    missing, by_setup = [], []
    for t in case.expected_tools:
        if t in SETUP_TOOLS.get(case.id, set()):
            by_setup.append(t)
            continue
        if t == "coach_chat":
            # coaching = grounded by the knowledge base, or answered/handled by a guardrail
            if used & READ_TOOLS or guard & {"refuse", "append_notice"}:
                continue
        elif t in used:
            continue
        missing.append(t)
    allowed_writes = {t for t in case.expected_tools if t in WRITE_TOOLS} - set(by_setup)
    unexpected = sorted(ok_writes - allowed_writes)
    return {"expected": list(case.expected_tools), "used": sorted(used), "missing": missing,
            "unexpected_writes": unexpected, "satisfied_by_setup": by_setup,
            "match": not missing and not unexpected}


# ---------------- (c) RAGAS ----------------
def contexts_for(trace: dict) -> list[str]:
    """Full text of retrieved docs (trace stores doc ids), in retrieval order, deduped."""
    by_doc: dict[str, list[str]] = {}
    for c in retriever.load_chunks():
        by_doc.setdefault(c["doc_id"], []).append(c["text"])
    out, seen = [], set()
    for d in trace.get("retrieved_chunks", []):
        if d in by_doc and d not in seen:
            seen.add(d)
            out.append(f"[{d}] " + " ".join(by_doc[d]))
    return out


def _ctx_block(contexts: list[str]) -> str:
    return "\n".join(f"[{i + 1}] {c}" for i, c in enumerate(contexts))


def faithfulness(judge, question: str, answer: str, contexts: list[str]) -> float:
    """Fraction of the answer's claims supported by the retrieved contexts."""
    claims = ask(judge, "faithfulness_claims",
                 f"QUESTION: {question}\nANSWER:\n{answer}\n\nBreak the answer into atomic factual "
                 'claims (skip greetings/offers). Return {"claims":["..."]}.').get("claims", [])
    if not claims:
        return 0.0
    res = ask(judge, "faithfulness_verdicts",
              f"CONTEXTS:\n{_ctx_block(contexts)}\n\nCLAIMS:\n"
              + "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
              + "\n\nFor each claim: 1 if it can be inferred from the contexts, else 0. "
                'Return {"verdicts":[0 or 1,...]} with one entry per claim.').get("verdicts", [])
    res = (list(res) + [0] * len(claims))[:len(claims)]
    return _clip(sum(1 for v in res if int(v) == 1) / len(claims))


def answer_relevancy(judge, question: str, answer: str) -> float:
    """RAGAS: questions generated from the answer should resemble the original question.
    Similarity is scored by the judge (no embedding model); noncommittal answers score 0."""
    out = ask(judge, "answer_relevancy",
              f"ORIGINAL QUESTION: {question}\nANSWER:\n{answer}\n\nGenerate 3 questions this "
              "answer would be a direct reply to. Rate each 0.0-1.0 for semantic similarity to "
              "the ORIGINAL QUESTION. Set noncommittal true if the answer evades/says it does "
              'not know. Return {"questions":[{"q":"...","similarity":0.0}],"noncommittal":false}.')
    if out.get("noncommittal"):
        return 0.0
    sims = [_clip(q.get("similarity", 0)) for q in out.get("questions", []) if isinstance(q, dict)]
    return sum(sims) / len(sims) if sims else 0.0


def ground_truth(case: Case) -> str:
    return "; ".join(case.expected_traits)


def context_precision(judge, question: str, case: Case, contexts: list[str]) -> float:
    """RAGAS average precision@k over ranked contexts, relevance judged vs question+reference."""
    out = ask(judge, "context_precision",
              f"QUESTION: {question}\nREFERENCE (ideal answer traits): {ground_truth(case)}\n"
              f"RANKED CONTEXTS:\n{_ctx_block(contexts)}\n\nFor each context, 1 if it is useful "
              'for answering the question per the reference, else 0. Return {"relevant":[0 or 1,...]}.')
    rel = [1 if int(v) == 1 else 0 for v in out.get("relevant", [])]
    rel = (rel + [0] * len(contexts))[:len(contexts)]
    if not any(rel):
        return 0.0
    hits, acc = 0, 0.0
    for k, r in enumerate(rel, 1):
        if r:
            hits += 1
            acc += hits / k
    return _clip(acc / hits)


def context_recall(judge, case: Case, contexts: list[str]) -> float:
    """RAGAS: share of reference statements attributable to the retrieved contexts."""
    stmts = case.expected_traits
    if not stmts:
        return 0.0
    out = ask(judge, "context_recall",
              f"CONTEXTS:\n{_ctx_block(contexts)}\n\nREFERENCE STATEMENTS:\n"
              + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(stmts))
              + "\n\nFor each statement 1 if supported by the contexts, else 0. "
                'Return {"attributed":[0 or 1,...]}.')
    att = (list(out.get("attributed", [])) + [0] * len(stmts))[:len(stmts)]
    return _clip(sum(1 for v in att if int(v) == 1) / len(stmts))


def ragas(judge, case: Case, reply: str, trace: dict) -> dict | None:
    """None when the case retrieved no knowledge (metrics not applicable)."""
    ctxs = contexts_for(trace)
    if not ctxs:
        return None
    return {"faithfulness": faithfulness(judge, case.input, reply, ctxs),
            "answer_relevancy": answer_relevancy(judge, case.input, reply),
            "context_precision": context_precision(judge, case.input, case, ctxs),
            "context_recall": context_recall(judge, case, ctxs)}


def leaked_secret(reply: str) -> bool:
    """True if any AWS credential value from the environment appears in the reply."""
    for n in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        v = os.environ.get(n, "")
        if len(v) >= 4 and v in reply:
            return True
    return False
