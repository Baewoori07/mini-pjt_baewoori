"""HTTP routes for CSS tests."""
from fastapi import APIRouter, Depends, HTTPException

from ..shared.web import get_conn
from . import repository
from .schemas import CssRequest
from .service import css_pace

router = APIRouter()


@router.post("/api/css")
def add_css(req: CssRequest, conn=Depends(get_conn)):
    if req.t400_s <= req.t200_s:
        raise HTTPException(422, "400m time must be slower than 200m time")
    pace = css_pace(req.t400_s, req.t200_s)
    cid = repository.add_css(conn, req.test_date.isoformat(), req.t400_s, req.t200_s, pace)
    return {"id": cid, "test_date": req.test_date.isoformat(), "t400_s": req.t400_s,
            "t200_s": req.t200_s, "css_pace_s_per_100m": pace}


@router.get("/api/css")
def get_css(conn=Depends(get_conn)):
    return repository.list_css(conn)
