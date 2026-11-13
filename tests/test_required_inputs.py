"""Required inputs: competition date, event, weekly sessions and duration.
Current event times are NOT required. Validation happens before any LLM call."""
import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.training_plan import service as planner
from src.main import create_app
from tests.test_plan_generation import FakeLLM, payload, body, n_weeks


@pytest.fixture
def comp():
    return date.today() + timedelta(weeks=10)


@pytest.mark.parametrize("field", ["competition_date", "event", "sessions_per_week",
                                   "session_minutes"])
def test_each_required_input_missing_is_rejected_before_llm(comp, field):
    llm = FakeLLM(lambda k: "{}")
    c = TestClient(create_app(llm, ":memory:"))
    b = body(comp)
    del b[field]
    assert c.post("/api/plan", json=b).status_code == 422
    assert llm.calls == []


def test_plan_created_without_current_times_and_covers_whole_period(comp):
    n = n_weeks(comp)
    llm = FakeLLM(lambda k: payload(n, 4, 90))
    c = TestClient(create_app(llm, ":memory:"))
    r = c.post("/api/plan", json=body(comp))  # no current event time supplied
    assert r.status_code == 200
    plan = r.json()
    assert [w["phase"] for w in plan["weeks"]][0] == "base"
    assert plan["weeks"][-1]["phase"] == "taper" and len(plan["weeks"]) == n
    assert len(plan["sessions"]) == 4
