import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.shared import db
from src.training_plan import service as planner
from src.main import create_app


class FakeLLM:
    def __init__(self, builder):
        self.builder = builder
        self.calls = []

    def complete(self, system, prompt):
        self.calls.append(prompt)
        return self.builder(len(self.calls))


def weeks_for(n):
    phases = []
    for i in range(n):
        phases.append("base" if i < n // 2 else "build" if i < n - max(1, n // 6) else "taper")
    return [{"week_number": i + 1, "phase": p} for i, p in enumerate(phases)]


def payload(n_weeks, sessions, minutes_per_session):
    sess = []
    for i in range(sessions):
        m = minutes_per_session
        sess.append({"title": f"S{i+1}", "sets": [
            {"type": "warm-up", "description": "easy", "distance_m": 400, "reps": 1,
             "intensity_rpe": 3, "est_minutes": m * 0.2},
            {"type": "main", "description": "8x100", "distance_m": 800, "reps": 8,
             "intensity_rpe": 8, "est_minutes": m * 0.6},
            {"type": "cool-down", "description": "easy", "distance_m": 200, "reps": 1,
             "intensity_rpe": 2, "est_minutes": m * 0.2}]})
    return json.dumps({"weeks": weeks_for(n_weeks), "sessions": sess})


@pytest.fixture
def comp():
    return date.today() + timedelta(weeks=12)


def body(comp, **kw):
    b = {"competition_date": comp.isoformat(), "event": "200m freestyle",
         "sessions_per_week": 4, "session_minutes": 90}
    b.update(kw)
    return b


def n_weeks(comp):
    return planner.count_weeks(date.today(), comp)


def test_full_plan_and_week_sessions_stored(comp):
    n = n_weeks(comp)
    llm = FakeLLM(lambda k: payload(n, 4, 90))
    client = TestClient(create_app(llm, ":memory:"))
    r = client.post("/api/plan", json=body(comp))
    assert r.status_code == 200
    plan = r.json()
    assert len(plan["weeks"]) == n
    phases = [w["phase"] for w in plan["weeks"]]
    assert set(phases) == {"base", "build", "taper"}
    order = {"base": 0, "build": 1, "taper": 2}
    assert [order[p] for p in phases] == sorted(order[p] for p in phases)
    assert len(plan["sessions"]) == 4
    for s in plan["sessions"]:
        assert sum(x["est_minutes"] for x in s["sets"]) <= 90
        assert all(1 <= x["intensity_rpe"] <= 10 for x in s["sets"])
        assert s["over_duration"] is False
    assert plan["warning"] is None and plan["regeneration_attempts"] == 0
    assert len(llm.calls) == 1
    again = client.get(f"/api/plan/{plan['id']}").json()
    assert again["weeks"] == plan["weeks"] and again["sessions"] == plan["sessions"]


def test_event_and_availability_variants(comp):
    n = n_weeks(comp)
    for sessions, minutes in [(3, 60), (5, 120)]:
        llm = FakeLLM(lambda k, s=sessions, m=minutes: payload(n, s, m))
        c = TestClient(create_app(llm, ":memory:"))
        r = c.post("/api/plan", json=body(comp, event="100m butterfly",
                                          sessions_per_week=sessions, session_minutes=minutes))
        assert r.status_code == 200
        assert len(r.json()["sessions"]) == sessions
        assert "100m butterfly" in llm.calls[0]


def test_over_duration_regenerates_then_succeeds(comp):
    n = n_weeks(comp)
    llm = FakeLLM(lambda k: payload(n, 4, 120 if k == 1 else 90))
    plan = TestClient(create_app(llm, ":memory:")).post("/api/plan", json=body(comp)).json()
    assert len(llm.calls) == 2 and plan["regeneration_attempts"] == 1
    assert plan["warning"] is None


def test_over_duration_capped_at_two_regenerations_then_warns(comp):
    n = n_weeks(comp)
    llm = FakeLLM(lambda k: payload(n, 4, 120))
    plan = TestClient(create_app(llm, ":memory:")).post("/api/plan", json=body(comp)).json()
    assert len(llm.calls) == 3 and plan["regeneration_attempts"] == 2
    assert plan["warning"] and all(s["over_duration"] for s in plan["sessions"])


def test_validation_errors(comp):
    c = TestClient(create_app(FakeLLM(lambda k: "{}"), ":memory:"))
    past = date.today() - timedelta(days=1)
    assert c.post("/api/plan", json=body(past)).status_code == 422
    assert c.post("/api/plan", json=body(comp, sessions_per_week=0)).status_code == 422
    assert c.post("/api/plan", json={"event": "x"}).status_code == 422


def test_bad_model_output_rejected(comp):
    c = TestClient(create_app(FakeLLM(lambda k: "not json"), ":memory:"))
    assert c.post("/api/plan", json=body(comp)).status_code == 502
    n = n_weeks(comp)
    bad = json.loads(payload(n, 4, 90))
    bad["weeks"][0]["phase"] = "taper"
    c = TestClient(create_app(FakeLLM(lambda k: json.dumps(bad)), ":memory:"))
    assert c.post("/api/plan", json=body(comp)).status_code == 502


def test_db_tables_created():
    conn = db.connect(":memory:")
    names = {r[0] for r in conn.execute("select name from sqlite_master where type='table'")}
    assert {"plans", "weeks", "sessions"} <= names
