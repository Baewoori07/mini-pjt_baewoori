import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.training_plan import service as planner
from src.main import create_app


class FakeLLM:
    def __init__(self, builder):
        self.builder = builder
        self.calls = []

    def complete(self, system, prompt):
        self.calls.append(prompt)
        return self.builder(len(self.calls))


COMP = date.today() + timedelta(weeks=8)
N = planner.count_weeks(date.today(), COMP)


def weeks():
    ph = ["base"] * (N - 3) + ["build"] * 2 + ["taper"]
    return [{"week_number": i + 1, "phase": p} for i, p in enumerate(ph)]


def sessions(total, count=3):
    return [{"title": f"S{i}", "sets": [
        {"type": "main", "description": "x", "distance_m": 100, "reps": 1,
         "intensity_rpe": 5, "est_minutes": total}]} for i in range(count)]


def plan_json(total):
    return json.dumps({"weeks": weeks(), "sessions": sessions(total)})


def week_json(total):
    return json.dumps({"sessions": sessions(total)})


BODY = {"competition_date": COMP.isoformat(), "event": "200m freestyle",
        "sessions_per_week": 3, "session_minutes": 60}


def client(llm):
    return TestClient(create_app(llm, ":memory:"))


def test_always_over_regenerates_exactly_twice_and_warns():
    llm = FakeLLM(lambda k: plan_json(100))
    r = client(llm).post("/api/plan", json=BODY)
    assert r.status_code == 200
    plan = r.json()
    assert len(llm.calls) == 3  # 1 initial + 2 regenerations
    assert plan["regeneration_attempts"] == 2
    assert plan["warning"]
    assert len(plan["sessions"]) == 3
    assert all(s["over_duration"] for s in plan["sessions"])


def test_retry_prompt_mentions_overrun():
    llm = FakeLLM(lambda k: plan_json(100))
    client(llm).post("/api/plan", json=BODY)
    assert "exceeded" in llm.calls[1] and "exceeded" in llm.calls[2]
    assert "exceeded" not in llm.calls[0]


def test_recovers_on_second_regeneration_no_warning():
    llm = FakeLLM(lambda k: plan_json(100 if k < 3 else 60))
    plan = client(llm).post("/api/plan", json=BODY).json()
    assert len(llm.calls) == 3 and plan["regeneration_attempts"] == 2
    assert plan["warning"] is None
    assert not any(s["over_duration"] for s in plan["sessions"])


def test_exactly_at_limit_is_not_over():
    llm = FakeLLM(lambda k: plan_json(60))
    plan = client(llm).post("/api/plan", json=BODY).json()
    assert len(llm.calls) == 1 and plan["warning"] is None


def test_only_one_session_over_triggers_retry_and_flags_it():
    def build(k):
        s = sessions(60)
        s[1]["sets"][0]["est_minutes"] = 75
        return json.dumps({"weeks": weeks(), "sessions": s})
    llm = FakeLLM(build)
    plan = client(llm).post("/api/plan", json=BODY).json()
    assert len(llm.calls) == 3
    flags = [s["over_duration"] for s in plan["sessions"]]
    assert flags == [False, True, False]
    assert plan["warning"]


def test_warning_persisted_flag_on_reload():
    llm = FakeLLM(lambda k: plan_json(100))
    c = client(llm)
    pid = c.post("/api/plan", json=BODY).json()["id"]
    again = c.get(f"/api/plan/{pid}").json()
    assert all(s["over_duration"] for s in again["sessions"])


def test_next_week_capped_and_warns():
    llm = FakeLLM(lambda k: plan_json(60) if k == 1 else week_json(100))
    c = client(llm)
    pid = c.post("/api/plan", json=BODY).json()["id"]
    before = len(llm.calls)
    r = c.post(f"/api/plan/{pid}/next-week")
    assert r.status_code == 200
    res = r.json()
    assert len(llm.calls) - before == 3
    assert res["regeneration_attempts"] == 2
    assert res["warning"]
    assert all(s["over_duration"] for s in res["sessions"])


def test_next_week_recovers_after_one_retry():
    state = {"n": 0}

    def build(k):
        if k == 1:
            return plan_json(60)
        state["n"] += 1
        return week_json(100 if state["n"] == 1 else 50)
    llm = FakeLLM(build)
    c = client(llm)
    pid = c.post("/api/plan", json=BODY).json()["id"]
    res = c.post(f"/api/plan/{pid}/next-week").json()
    assert res["regeneration_attempts"] == 1 and res["warning"] is None


def test_planner_level_cap():
    llm = FakeLLM(lambda k: plan_json(100))
    out = planner.generate_plan(llm, {k: v for k, v in BODY.items()})
    assert out["regeneration_attempts"] == planner.MAX_REGENERATIONS == 2
    assert len(llm.calls) == 3


def test_ui_shows_warning():
    html = open("static/index.html", encoding="utf-8").read()
    assert 'id="warn"' in html and "o.warning" in html
