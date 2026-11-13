"""Request/response types of the coach agent (POST /api/chat, POST /query - spec 4-2)."""
from typing import TypedDict

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    plan_id: int | None = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)



class ContextOut(TypedDict):
    doc_id: str
    title: str
    text: str


class TraceStep(TypedDict):
    step: str      # guardrail_input | retrieve | llm | tool:<name> | guardrail_output
    input: str
    output: str


class AgentResult(TypedDict):
    reply: str
    tools_used: list[str]
    steps: int
    contexts: list[ContextOut]
    trace: list[TraceStep]
