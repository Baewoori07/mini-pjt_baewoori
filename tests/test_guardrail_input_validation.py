"""G-04: invalid input is rejected with a 4xx + reason before any Bedrock call."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from tests.test_plan_generation import FakeLLM, body, payload, n_weeks

TODAY = date.today()
FUTURE = TODAY + timedelta(weeks=10)


def client():
    llm = FakeLLM(lambda k: "{}")
    return TestClient(create_app(llm, ":memory:")), llm


def reason(r):
    assert 400 <= r.status_code < 500
    detail = r.json()["detail"]
    assert detail  # non-empty reason message
    return str(detail)


@pytest.mark.parametrize("past", [TODAY - timedelta(days=1), TODAY, TODAY - timedelta(weeks=20)])
def test_past_competition_date_rejected(past):
    c, llm = client()
    r = c.post("/api/plan", json=body(past))
    assert "competition_date" in reason(r)
    assert llm.calls == []


@pytest.mark.parametrize("field,value", [
    ("sessions_per_week", 0), ("sessions_per_week", -3),
    ("session_minutes", 0), ("session_minutes", -60)])
def test_non_positive_availability_rejected(field, value):
    c, llm = client()
    r = c.post("/api/plan", json=body(FUTURE, **{field: value}))
    assert field in reason(r)
    assert llm.calls == []


@pytest.mark.parametrize("event", [
    "underwater basket weaving", "300m freestyle", "1500m butterfly", "200m", "freestyle",
    "100m dolphin", "10000m freestyle", "   "])
def test_unsupported_event_rejected(event):
    c, llm = client()
    r = c.post("/api/plan", json=body(FUTURE, event=event))
    assert "event" in reason(r)
    assert llm.calls == []


@pytest.mark.parametrize("event", ["200m freestyle", "100m butterfly", "200m IM",
                                   "1500m Freestyle", "50m breaststroke", "100m backstroke"])
def test_supported_events_still_accepted(event):
    n = n_weeks(FUTURE)
    llm = FakeLLM(lambda k: payload(n, 4, 90))
    c = TestClient(create_app(llm, ":memory:"))
    assert c.post("/api/plan", json=body(FUTURE, event=event)).status_code == 200
    assert len(llm.calls) == 1


@pytest.mark.parametrize("t400,t200", [(120, 120), (100, 130), (300, 300.0)])
def test_css_200_not_faster_than_400_rejected_and_not_stored(t400, t200):
    c, llm = client()
    r = c.post("/api/css", json={"test_date": TODAY.isoformat(), "t400_s": t400, "t200_s": t200})
    reason(r)
    assert c.get("/api/css").json() == []
    assert llm.calls == []


def test_valid_css_is_stored():
    c, _ = client()
    r = c.post("/api/css", json={"test_date": TODAY.isoformat(), "t400_s": 300, "t200_s": 140})
    assert r.status_code == 200
    assert len(c.get("/api/css").json()) == 1
