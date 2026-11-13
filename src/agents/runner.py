"""Main SwimCoach agent: Claude tool-use loop for POST /api/chat (Bedrock Messages API).

Flow: input guardrail -> [LLM -> tool calls (src/agent_tools) -> tool results]* (max 8 steps)
-> output guardrail -> JSONL trace.

Tools are executed by app code. Write tools are gated by explicit user intent (G-03), so a
coaching-only question can never change stored set tables.
"""
import json

from .. import guardrails
from ..agent_tools import READ_TOOLS, TOOLS, WRITE_TOOLS, ToolContext
from ..knowledge import search_knowledge
from ..shared import tracing
from ..shared.redaction import redact
from .prompts import FALLBACK, prefetch_block, system_prompt
from .schemas import AgentResult


MAX_STEPS = 8


def _text(blocks) -> str:
    return "".join(b.text for b in blocks if getattr(b, "type", "") == "text")


def _as_param(b) -> dict:
    if b.type == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
    return {"type": "text", "text": getattr(b, "text", "")}


PREFETCH_K = 3


def _short(x, limit: int = 300) -> str:
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False, default=str)
    s = redact(s)
    return s if len(s) <= limit else s[:limit] + "…"


def _contexts(chunks: list[dict]) -> list[dict]:
    seen, out = set(), []
    for c in chunks:
        key = (c["doc_id"], c["text"])
        if key not in seen:
            seen.add(key)
            out.append({"doc_id": c["doc_id"], "title": c.get("title", ""), "text": c["text"]})
    return out


def run_agent(llm, conn, message: str, plan_id: int | None = None,
              history: list[dict] | None = None, prefetch: bool = True) -> AgentResult:
    """Agent graph: guard_in -> retrieve -> (llm -> tools)* -> guard_out.

    Returns {"reply", "tools_used", "steps", "contexts": [{doc_id,title,text}],
             "trace": [{"step","input","output"}]} - the last two feed POST /query.
    """
    trace: list[dict] = []
    verdict = guardrails.check_input(message)
    trace.append({"step": "guardrail_input", "input": _short(message),
                  "output": "allow" if verdict.allowed else f"refuse ({verdict.rule})"})
    if not verdict.allowed:
        tracing.set_final_answer(verdict.refusal)
        return {"reply": verdict.refusal, "tools_used": [], "steps": 0, "contexts": [],
                "trace": trace}
    system = guardrails.safety_system(system_prompt(), verdict)
    msgs = [{"role": m["role"], "content": redact(m["content"])} for m in (history or [])[-10:]
            if m["role"] in ("user", "assistant")]
    hits = search_knowledge(message, k=PREFETCH_K) if prefetch else []
    if prefetch:
        tracing.record_tool_call("search_knowledge", {"query": message, "k": PREFETCH_K,
                                                      "internal": "prefetch"},
                                 [{"doc_id": h["doc_id"], "title": h["title"]} for h in hits])
        trace.append({"step": "retrieve", "input": _short(message),
                      "output": _short([f"{h['doc_id']}: {h['title']}" for h in hits])})
    user_text = redact(message) if not hits else f"{prefetch_block(hits)}\n\n[사용자 질문]\n{redact(message)}"
    msgs.append({"role": "user", "content": user_text})
    ctx = ToolContext(llm, conn, plan_id, message)
    used: list[str] = []
    reply, steps, finished = "", 0, False
    for steps in range(1, MAX_STEPS + 1):
        resp = llm.chat(redact(system), msgs, TOOLS)
        blocks = list(getattr(resp, "content", None) or [])
        calls = [b for b in blocks if getattr(b, "type", "") == "tool_use"]
        trace.append({"step": "llm", "input": f"turn {steps}",
                      "output": _short([f"tool_use:{c.name}" for c in calls] or _text(blocks))})
        if not calls:
            reply, finished = _text(blocks), True
            break
        msgs.append({"role": "assistant", "content": [_as_param(b) for b in blocks]})
        results = []
        for c in calls:
            if c.name not in used:
                used.append(c.name)
            try:
                if c.name not in READ_TOOLS + WRITE_TOOLS:
                    raise ValueError(f"unknown tool {c.name}")
                out, err = ctx.run(c.name, dict(c.input or {})), False
            except Exception as e:  # tool errors go back to the model
                out, err = {"error": str(e)}, True
            tracing.record_tool_call(c.name, dict(c.input or {}), out, err)
            trace.append({"step": "retrieve" if c.name == "search_knowledge" else f"tool:{c.name}",
                          "input": _short(dict(c.input or {})),
                          "output": ("ERROR " if err else "") + _short(out)})
            results.append({"type": "tool_result", "tool_use_id": c.id, "is_error": err,
                            "content": redact(json.dumps(out, ensure_ascii=False, default=str))})
        msgs.append({"role": "user", "content": results})
    if not finished:
        reply = FALLBACK
    reply = guardrails.check_output(reply or FALLBACK, verdict)
    trace.append({"step": "guardrail_output", "input": "reply", "output": "checked (G-02/G-03/G-05)"})
    tracing.set_final_answer(redact(reply))
    return {"reply": redact(reply), "tools_used": used, "steps": steps,
            "contexts": _contexts(hits + ctx.contexts), "trace": trace}
