"""Evaluation runner:  uv run python -m evaluation.run --round N  [--cases 1,2] [--out DIR]

Only this entry point (main) makes live Bedrock calls; run_round() takes injected clients so the
tests can use mocks. Never prints or writes .env values.
"""
import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from src import agents as agent
from src.shared import db, tracing
from src.shared.redaction import redact
from . import cases as cases_mod
from . import metrics, report

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "global.anthropic.claude-sonnet-4-6"


class QuotaExhausted(RuntimeError):
    """A daily quota error makes the remaining cases meaningless, so the round stops."""


def run_case(app_llm, judge, case) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        conn = db.connect(str(Path(tmp) / "eval.db"))
        reply, error, trace, t = "", None, {}, None
        try:
            plan_id = cases_mod.prepare(conn, case)
            try:
                msg = cases_mod.user_message(case)
                with tracing.request_trace("chat", msg) as t:
                    out = agent.run_agent(tracing.TracedLLM(app_llm), conn, msg, plan_id, [])
                    reply = out["reply"]
                    trace = t.to_dict()
            except Exception as e:  # the agent failed; still score what we have
                error = f"{type(e).__name__}: {e}"
                trace = t.to_dict() if t else {}
            reply = redact(reply)
            tm = metrics.tool_match(case, trace)
            try:
                jd = metrics.judge_case(judge, case, reply, trace, metrics.leaked_secret(reply))
            except Exception as e:
                jd = {"verdict": "fail", "score": 1, "reason": f"심판 호출 실패: {redact(str(e))}"}
                error = error or f"judge: {redact(str(e))}"
            try:
                rg = metrics.ragas(judge, case, reply, trace)
            except Exception as e:
                rg, error = None, error or f"ragas: {redact(str(e))}"
        finally:
            conn.close()
    llm_calls = trace.get("llm_calls", [])
    tin = sum(c.get("input_tokens") or 0 for c in llm_calls)
    tout = sum(c.get("output_tokens") or 0 for c in llm_calls)
    return {"id": case.id, "category": case.category, "input": case.input, "reply": reply,
            "passed": jd["verdict"] == "pass" and tm["match"]
            and (error is None or error.startswith("ragas")),
            "judge": jd, "tool_match": tm, "ragas": rg,
            "latency_ms": trace.get("total_latency_ms", 0.0),
            "tokens": {"input": tin, "output": tout, "total": tin + tout},
            "retrieved_chunks": trace.get("retrieved_chunks", []),
            "guardrails": trace.get("guardrails", []), "error": error}


def run_round(n: int, app_llm, judge, out_dir: Path | None = None, cases_path: Path | None = None,
              only: set[int] | None = None, meta: dict | None = None) -> dict:
    out_dir = Path(out_dir or ROOT / "evaluation")
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = cases_mod.load_cases(cases_path or cases_mod.CASES_PATH)
    if only:
        cases = [c for c in cases if c.id in only]
    old_trace_dir = os.environ.get("TRACE_DIR")
    os.environ["TRACE_DIR"] = str(out_dir / "traces" / f"round{n}")
    try:
        results = []
        for c in cases:
            r = run_case(app_llm, judge, c)
            results.append(r)
            if r["error"] and "per day" in r["error"]:
                raise QuotaExhausted(
                    f"case {c.id}: Bedrock daily token quota exhausted; round {n} aborted, "
                    "no report written")
    finally:
        if old_trace_dir is None:
            os.environ.pop("TRACE_DIR", None)
        else:
            os.environ["TRACE_DIR"] = old_trace_dir
    summary = report.summarize(results)
    meta = {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), **(meta or {})}
    prev = report.load_previous(out_dir, n)
    data = {"round": n, "meta": meta, "summary": summary, "cases": results}
    (out_dir / f"round{n}_results.json").write_text(
        redact(json.dumps(data, ensure_ascii=False, indent=2)), encoding="utf-8")
    (out_dir / f"round{n}_report.md").write_text(
        redact(report.build_report(n, summary, results, meta, prev)), encoding="utf-8")
    return data


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="SwimCoach self-evaluation round")
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--cases", help="comma-separated case ids (default: all)")
    ap.add_argument("--out", help="output directory (default: evaluation/)")
    ap.add_argument("--changes", help="markdown file describing changes since the previous round")
    args = ap.parse_args(argv)

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")  # explicit path
    from src.shared.llm import BedrockLLM
    app_model = os.environ.get("BEDROCK_MODEL_ID") or DEFAULT_MODEL
    judge_model = os.environ.get("JUDGE_MODEL_ID") or DEFAULT_MODEL
    only = {int(x) for x in args.cases.split(",")} if args.cases else None
    data = run_round(args.round, BedrockLLM(app_model), BedrockLLM(judge_model),
                     Path(args.out) if args.out else None, only=only,
                     meta={"app_model": app_model, "judge_model": judge_model,
                           **({"changes": Path(args.changes).read_text(encoding="utf-8")}
                              if args.changes else {})})
    s = data["summary"]
    print(f"round {args.round}: overall {s['passed']}/{s['total']} "
          f"({(s['overall_pass_rate'] or 0) * 100:.1f}%), guardrail "
          f"{(s['guardrail_pass_rate'] or 0) * 100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
