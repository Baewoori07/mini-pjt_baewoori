import json
from datetime import date, timedelta

from fastapi.testclient import TestClient

from src.training_plan import service as planner
from src.main import create_app
from tests.test_plan_generation import FakeLLM, body, payload


def week_payload(sessions, minutes):
    return json.dumps({"sessions": json.loads(payload(1, sessions, minutes))["sessions"]})


def setup():
    comp = date.today() + timedelta(weeks=12)
    n = planner.count_weeks(date.today(), comp)

    def build(k):
        if k == 1:
            return payload(n, 4, 90)
        if "Generate week" in llm.calls[-1]:
            return week_payload(4, 90)
        return "Keep your elbow high during catch; try fingertip drag drill."
    llm = FakeLLM(build)
    c = TestClient(create_app(llm, ":memory:"))
    pid = c.post("/api/plan", json=body(comp)).json()["id"]
    return c, llm, pid


def test_logs_and_css_stored_and_used_in_next_week():
    c, llm, pid = setup()
    r = c.post(f"/api/plan/{pid}/logs", json={"log_date": date.today().isoformat(),
               "distance_m": 3000, "perceived_rpe": 7, "notes": "shoulder tight",
               "completed_sets": "all"})
    assert r.status_code == 200
    assert c.get(f"/api/plan/{pid}/logs").json()[0]["notes"] == "shoulder tight"
    css = c.post("/api/css", json={"test_date": date.today().isoformat(),
                                   "t400_s": 300, "t200_s": 140}).json()
    assert css["css_pace_s_per_100m"] == 80.0
    assert len(c.get("/api/css").json()) == 1
    r = c.post(f"/api/plan/{pid}/next-week")
    assert r.status_code == 200 and len(r.json()["sessions"]) == 4
    assert r.json()["week"]["week_number"] == 2
    prompt = llm.calls[-1]
    assert "shoulder tight" in prompt and "CSS pace 80.0" in prompt and "pace" in prompt.lower()
    plan = c.get(f"/api/plan/{pid}").json()
    assert {s["week_number"] for s in plan["sessions"]} == {1, 2}


def test_next_week_without_history_uses_rpe_only():
    c, llm, pid = setup()
    assert c.post(f"/api/plan/{pid}/next-week").status_code == 200
    assert "cycle-time" not in llm.calls[-1]


def test_next_week_over_duration_cap():
    comp = date.today() + timedelta(weeks=12)
    n = planner.count_weeks(date.today(), comp)
    llm = FakeLLM(lambda k: payload(n, 4, 90) if k == 1 else week_payload(4, 120))
    c = TestClient(create_app(llm, ":memory:"))
    pid = c.post("/api/plan", json=body(comp)).json()["id"]
    r = c.post(f"/api/plan/{pid}/next-week").json()
    assert len(llm.calls) == 4 and r["regeneration_attempts"] == 2 and r["warning"]


def test_validation_and_404():
    c, _, pid = setup()
    assert c.post("/api/css", json={"test_date": "2026-01-01", "t400_s": 100, "t200_s": 140}).status_code == 422
    assert c.post(f"/api/plan/{pid}/logs", json={"log_date": "2026-01-01", "perceived_rpe": 11}).status_code == 422
    assert c.post("/api/plan/999/logs", json={"log_date": "2026-01-01", "perceived_rpe": 5}).status_code == 404
    assert c.post("/api/plan/999/next-week").status_code == 404


def test_coaching_qa_read_only_with_context():
    c, llm, pid = setup()
    c.post(f"/api/plan/{pid}/logs", json={"log_date": date.today().isoformat(),
           "perceived_rpe": 8, "notes": "dropped elbow"})
    before = c.get(f"/api/plan/{pid}").json()
    r = c.post("/api/coach", json={"message": "How do I fix my catch?", "plan_id": pid})
    assert r.status_code == 200 and "drill" in r.json()["reply"]
    p = llm.calls[-1]
    assert "200m freestyle" in p and "dropped elbow" in p and "How do I fix my catch?" in p
    assert c.get(f"/api/plan/{pid}").json() == before
    c.post("/api/coach", json={"message": "and breathing?", "plan_id": pid})
    assert "How do I fix my catch?" in llm.calls[-1]
    assert len(c.get("/api/coach/history", params={"plan_id": pid}).json()) == 4
    assert c.post("/api/coach", json={"message": ""}).status_code == 422
    assert c.post("/api/coach", json={"message": "hi"}).status_code == 200
