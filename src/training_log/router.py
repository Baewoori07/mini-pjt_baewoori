"""HTTP routes for training logs."""
from fastapi import APIRouter, Depends

from ..shared.web import get_conn
from ..training_plan.service import need_plan
from . import repository
from .schemas import LogRequest

router = APIRouter()


@router.post("/api/plan/{plan_id}/logs")
def add_log(plan_id: int, req: LogRequest, conn=Depends(get_conn)):
    need_plan(conn, plan_id)
    d = req.model_dump(mode="json")
    d["id"] = repository.add_log(conn, plan_id, d)
    return d


@router.get("/api/plan/{plan_id}/logs")
def get_logs(plan_id: int, conn=Depends(get_conn)):
    need_plan(conn, plan_id)
    return repository.list_logs(conn, plan_id)
