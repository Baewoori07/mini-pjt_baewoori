"""HTTP route for chat history."""
from fastapi import APIRouter, Depends

from ..shared.web import get_conn
from . import repository

router = APIRouter()


@router.get("/api/coach/history")
def coach_history(plan_id: int | None = None, conn=Depends(get_conn)):
    return repository.list_messages(conn, plan_id)
