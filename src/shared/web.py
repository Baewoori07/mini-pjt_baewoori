"""FastAPI dependencies shared by every domain router."""
from fastapi import Request

from . import tracing
from .llm import BedrockLLM, LLMClient


def get_conn(request: Request):
    return request.app.state.conn


def get_llm(request: Request) -> LLMClient:
    """Lazily create the Bedrock client (tests inject a fake) and wrap it for tracing."""
    state = request.app.state
    if state.llm is None:
        state.llm = BedrockLLM()
    llm = state.llm
    return llm if isinstance(llm, tracing.TracedLLM) else tracing.TracedLLM(llm)
