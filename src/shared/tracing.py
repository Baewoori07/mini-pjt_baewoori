"""Local JSONL request tracing (no external service).

``request_trace(kind, input)`` wraps one chat/plan request. Hooks elsewhere in the app record into
the active trace via contextvars: ``TracedLLM`` (LLM calls), the agent loop (tool calls),
``knowledge.search_knowledge`` (chunk ids) and ``guardrails.check_input/check_output`` (decisions).
On exit one JSON line is appended to ``traces/<YYYY-MM-DD>.jsonl`` (override dir: TRACE_DIR).
Every string is passed through ``shared.redaction.redact`` so AWS credential values never reach disk.
"""
import contextvars
import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .redaction import redact

TRACE_DIR = Path(__file__).resolve().parents[2] / "traces"
_current: contextvars.ContextVar["Trace | None"] = contextvars.ContextVar("trace", default=None)
_lock = threading.Lock()
SUMMARY_MAX = 300


def trace_dir() -> Path:
    return Path(os.environ.get("TRACE_DIR") or TRACE_DIR)


def _clean(obj):
    """Recursively redact credential values from a JSON-able structure."""
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        return {redact(str(k)): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (int, float, bool)) or obj is None:
        return obj
    return redact(str(obj))


def summarize(obj, limit: int = SUMMARY_MAX) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + "…"


class Trace:
    def __init__(self, kind: str, input_text: str):
        self.request_id = uuid.uuid4().hex
        self.kind = kind
        self.input = input_text
        self.llm_calls: list[dict] = []
        self.tool_calls: list[dict] = []
        self.retrieved_chunks: list[str] = []
        self.guardrails: list[dict] = []
        self.final_answer = ""
        self.error: str | None = None
        self._t0 = time.perf_counter()
        self.started_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return _clean({
            "request_id": self.request_id, "kind": self.kind, "started_at": self.started_at,
            "input": self.input, "llm_calls": self.llm_calls, "tool_calls": self.tool_calls,
            "retrieved_chunks": self.retrieved_chunks, "guardrails": self.guardrails,
            "final_answer": self.final_answer, "error": self.error,
            "total_latency_ms": round((time.perf_counter() - self._t0) * 1000, 1)})


def current() -> Trace | None:
    return _current.get()


def record_llm_call(model: str, latency_ms: float, input_tokens, output_tokens,
                    error: str | None = None) -> None:
    t = current()
    if t:
        t.llm_calls.append({"model": model, "latency_ms": round(latency_ms, 1),
                            "input_tokens": input_tokens, "output_tokens": output_tokens,
                            "error": error})


def record_tool_call(name: str, args: dict, result, is_error: bool = False) -> None:
    t = current()
    if t:
        t.tool_calls.append({"name": name, "args": args, "result_summary": summarize(result),
                             "is_error": is_error})


def record_chunks(chunk_ids: list[str]) -> None:
    t = current()
    if t:
        t.retrieved_chunks.extend(chunk_ids)


def record_guardrail(stage: str, rule: str | None, decision: str, detail: str = "") -> None:
    t = current()
    if t:
        t.guardrails.append({"stage": stage, "rule": rule, "decision": decision, "detail": detail})


def set_final_answer(answer) -> None:
    t = current()
    if t:
        t.final_answer = answer if isinstance(answer, str) else summarize(answer, 2000)


def write_trace(t: Trace) -> Path:
    d = trace_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    line = redact(json.dumps(t.to_dict(), ensure_ascii=False, default=str))
    with _lock, open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    return path


@contextmanager
def request_trace(kind: str, input_text: str):
    """Always writes exactly one line, even if the request raises."""
    t = Trace(kind, input_text)
    token = _current.set(t)
    try:
        yield t
    except BaseException as e:
        t.error = f"{type(e).__name__}: {e}"
        raise
    finally:
        _current.reset(token)
        try:
            write_trace(t)
        except OSError:
            pass  # tracing must never break a request


def _usage(resp) -> tuple:
    u = getattr(resp, "usage", None)
    return getattr(u, "input_tokens", None), getattr(u, "output_tokens", None)


class TracedLLM:
    """Wraps any LLM client; records model id, latency and token usage of each call."""

    def __init__(self, inner):
        self._inner = inner

    @property
    def model_id(self) -> str:
        return getattr(self._inner, "model_id", type(self._inner).__name__)

    def __getattr__(self, name):  # delegate anything else (e.g. test fakes' attributes)
        return getattr(self._inner, name)

    def _timed(self, fn, *a):
        t0 = time.perf_counter()
        try:
            out = fn(*a)
        except Exception as e:
            record_llm_call(self.model_id, (time.perf_counter() - t0) * 1000, None, None,
                            f"{type(e).__name__}: {e}")
            raise
        return out, (time.perf_counter() - t0) * 1000

    def complete(self, system: str, prompt: str) -> str:
        out, ms = self._timed(self._inner.complete, system, prompt)
        u = getattr(self._inner, "last_usage", None) or (None, None)
        record_llm_call(self.model_id, ms, *u)
        return out

    def chat(self, system: str, messages: list, tools: list):
        out, ms = self._timed(self._inner.chat, system, messages, tools)
        record_llm_call(self.model_id, ms, *_usage(out))
        return out
