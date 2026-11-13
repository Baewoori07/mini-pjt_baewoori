"""HTTP routes of the coach agent: POST /api/chat (web UI) and POST /query (spec 4-2)."""
from fastapi import APIRouter, Depends

from ..memory import repository as memory
from ..shared import tracing
from ..shared.redaction import redact
from ..shared.web import get_conn, get_llm
from ..training_plan.service import need_plan
from .runner import run_agent
from .schemas import ChatRequest, QueryRequest

router = APIRouter()


@router.post("/api/chat")
def chat(req: ChatRequest, conn=Depends(get_conn), llm=Depends(get_llm)):
    if req.plan_id is not None:
        need_plan(conn, req.plan_id)
    history = memory.list_messages(conn, req.plan_id)
    with tracing.request_trace("chat", req.message):
        out = run_agent(llm, conn, req.message, req.plan_id, history)
    memory.add_message(conn, req.plan_id, "user", redact(req.message))
    memory.add_message(conn, req.plan_id, "assistant", redact(out["reply"]))
    return {"reply": out["reply"], "tools_used": out["tools_used"], "steps": out["steps"]}


@router.post("/query")
def query(req: QueryRequest, conn=Depends(get_conn), llm=Depends(get_llm)):
    """Standard API (spec 4-2): {"question"} -> {"answer", "contexts", "trace"}."""
    with tracing.request_trace("query", req.question):
        out = run_agent(llm, conn, req.question, None, [])
    return {"answer": out["reply"],
            "contexts": [{"doc_id": c["doc_id"], "text": c["text"]} for c in out["contexts"]],
            "trace": out["trace"]}
