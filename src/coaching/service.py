"""Text-only coaching Q&A. Plan and logs are read-only context; sets are never modified."""
from .. import guardrails, knowledge
from ..guardrails import MEDICAL_NOTICE as NOTICE_KO  # noqa: F401
from ..shared.llm import LLMClient
from ..shared.redaction import redact
from .prompts import SYSTEM, build_prompt


NOTICE_EN = NOTICE_KO  # safety notices are Korean only (G-02)


def guard_refusal(question: str) -> str | None:
    """Korean refusal if the question must not reach the model, else None (G-03/G-05)."""
    return guardrails.check_input(question).refusal


class _RedactingLLM:
    """Wraps an LLM client so no credential value reaches the model or comes back from it."""

    def __init__(self, inner: LLMClient):
        self.inner = inner

    def complete(self, system: str, prompt: str) -> str:
        return redact(self.inner.complete(redact(system), redact(prompt)))


class _KnowledgeLLM:
    """Adds retrieved knowledge excerpts to the prompt (RAG)."""

    def __init__(self, inner: LLMClient, context: str):
        self.inner, self.context = inner, context

    def complete(self, system: str, prompt: str) -> str:
        return self.inner.complete(system + " Ground answers in the knowledge excerpts when relevant.",
                                   self.context + "\n" + prompt)


def answer(llm: LLMClient, question: str, plan, logs, css, history) -> str:
    """input check (G-02/03/05) -> agent loop (RAG + model) -> output check."""
    verdict = guardrails.check_input(question)
    if not verdict.allowed:
        return verdict.refusal
    hits = knowledge.search_knowledge(question, k=3)
    agent_llm = _RedactingLLM(_KnowledgeLLM(llm, knowledge.format_context(hits)) if hits else llm)
    system = guardrails.safety_system(SYSTEM, verdict)
    reply = agent_llm.complete(system, build_prompt(question, plan, logs, css, history))
    reply = guardrails.check_output(reply, verdict)
    if hits:
        reply = f"{reply}\n\n{knowledge.sources_line(hits)}"
    return redact(reply)
