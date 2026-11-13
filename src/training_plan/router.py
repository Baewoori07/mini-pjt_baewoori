"""HTTP routes for plans and set tables."""
import json

from fastapi import APIRouter, Depends, HTTPException

from .. import guardrails
from ..shared import tracing
from ..shared.web import get_conn, get_llm
from ..training_log import repository as log_repo
from ..css_test import repository as css_repo
from . import repository, service
from .schemas import PlanError, PlanRequest
from .service import need_plan

router = APIRouter()


@router.post("/api/plan")
def create_plan(req: PlanRequest, conn=Depends(get_conn), llm=Depends(get_llm)):
    inputs = {"competition_date": req.competition_date.isoformat(), "event": req.event,
              "sessions_per_week": req.sessions_per_week,
              "session_minutes": req.session_minutes}
    with tracing.request_trace("plan", json.dumps(inputs, ensure_ascii=False)):
        try:
            result = service.generate_plan(llm, inputs)
        except PlanError as e:
            raise HTTPException(502, f"plan generation failed: {e}")
        pid = repository.save_plan(conn, inputs=inputs, **result)
        plan = repository.get_plan(conn, pid)
        plan["warning"] = (guardrails.DURATION_WARNING
                           if any(s["over_duration"] for s in plan["sessions"]) else None)
        over = [s["over_duration"] for s in plan["sessions"]]
        tracing.record_guardrail("output", "G-01", "warn" if any(over) else "pass",
                                 f"{sum(over)}/{len(over)} sessions over duration; "
                                 f"regenerations={result.get('regeneration_attempts')}")
        tracing.set_final_answer(f"plan_id={pid} weeks={len(plan['weeks'])} "
                                 f"sessions={len(plan['sessions'])}")
        return plan


@router.get("/api/plans/latest")
def latest_plan(conn=Depends(get_conn)):
    """Most recent plan id (the page restores it on reload); null when none exists."""
    return {"id": repository.latest_plan_id(conn)}


@router.get("/api/plan/{plan_id}")
def read_plan(plan_id: int, conn=Depends(get_conn)):
    return need_plan(conn, plan_id)


@router.post("/api/plan/{plan_id}/next-week")
def next_week(plan_id: int, conn=Depends(get_conn), llm=Depends(get_llm)):
    plan = need_plan(conn, plan_id)
    done = max([s["week_number"] for s in plan["sessions"]] or [0])
    if done >= len(plan["weeks"]):
        raise HTTPException(409, "plan has no further weeks")
    week = plan["weeks"][done]
    with tracing.request_trace("next_week", f"plan_id={plan_id} week={week['week_number']}"):
        try:
            res = service.generate_next_week(llm, plan, week, log_repo.list_logs(conn, plan_id),
                                             css_repo.list_css(conn))
        except PlanError as e:
            raise HTTPException(502, f"next week generation failed: {e}")
        tracing.set_final_answer(f"week={week['week_number']} sessions={len(res['sessions'])}")
    repository.add_week_sessions(conn, plan_id, week["week_number"], res["sessions"])
    return {"week": week, "sessions": res["sessions"],
            "regeneration_attempts": res["regeneration_attempts"],
            "warning": (guardrails.DURATION_WARNING
                        if any(s["over_duration"] for s in res["sessions"]) else None)}
