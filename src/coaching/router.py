"""HTTP route of the text-only coach (POST /api/coach)."""
from fastapi import APIRouter, Depends

from ..css_test import repository as css_repo
from ..memory import repository as memory
from ..shared import tracing
from ..shared.redaction import redact
from ..shared.web import get_conn, get_llm
from ..training_log import repository as log_repo
from ..training_plan.service import need_plan
from . import service
from .schemas import CoachRequest

router = APIRouter()


@router.post("/api/coach")
def coach_chat(req: CoachRequest, conn=Depends(get_conn), llm=Depends(get_llm)):
    plan = need_plan(conn, req.plan_id) if req.plan_id is not None else None
    logs = log_repo.list_logs(conn, req.plan_id) if plan else []
    history = memory.list_messages(conn, req.plan_id)
    with tracing.request_trace("coach", req.message):
        reply = service.answer(llm, req.message, plan, logs, css_repo.list_css(conn), history)
        tracing.set_final_answer(reply)
    memory.add_message(conn, req.plan_id, "user", redact(req.message))
    memory.add_message(conn, req.plan_id, "assistant", redact(reply))
    return {"reply": reply}
