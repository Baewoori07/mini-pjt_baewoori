"""AC: logs + CSS results are stored/retrieved and passed into the next-week prompt."""
import json
from datetime import date, timedelta

from fastapi.testclient import TestClient

from src.shared import db
from src.css_test import repository as css_repo
from src.training_log import repository as log_repo
from src.training_plan import service as planner
from src.main import create_app
from tests.test_plan_generation import FakeLLM, body, payload


def _week(sessions=4, minutes=90):
    return json.dumps({"sessions": json.loads(payload(1, sessions, minutes))["sessions"]})


def _client():
    comp = date.today() + timedelta(weeks=12)
    n = planner.count_weeks(date.today(), comp)
    llm = FakeLLM(lambda k: payload(n, 4, 90) if k == 1 else _week())
    c = TestClient(create_app(llm, ":memory:"))
    pid = c.post("/api/plan", json=body(comp)).json()["id"]
    return c, llm, pid


def test_db_roundtrip_logs_and_css():
    conn = db.connect(":memory:")
    conn.execute("INSERT INTO plans (competition_date,event,sessions_per_week,session_minutes,"
                 "start_date) VALUES ('2030-01-01','200 free',4,90,'2029-01-01')")
    log_repo.add_log(conn, 1, {"log_date": "2029-01-02", "perceived_rpe": 6, "notes": "n1",
                         "distance_m": 2500})
    css_repo.add_css(conn, "2029-01-03", 300.0, 140.0, 80.0)
    assert log_repo.list_logs(conn, 1)[0]["notes"] == "n1"
    assert css_repo.list_css(conn)[0]["css_pace_s_per_100m"] == 80.0


def test_api_save_and_retrieve():
    c, _, pid = _client()
    assert c.post(f"/api/plan/{pid}/logs", json={
        "log_date": date.today().isoformat(), "distance_m": 3000, "perceived_rpe": 7,
        "notes": "left shoulder tight", "completed_sets": "all"}).status_code == 200
    assert c.post("/api/css", json={"test_date": date.today().isoformat(),
                                    "t400_s": 300, "t200_s": 140}).status_code == 200
    logs = c.get(f"/api/plan/{pid}/logs").json()
    css = c.get("/api/css").json()
    assert logs[0]["notes"] == "left shoulder tight" and logs[0]["distance_m"] == 3000
    assert css[0]["css_pace_s_per_100m"] == 80.0


def test_next_week_prompt_contains_logs_and_css():
    c, llm, pid = _client()
    c.post(f"/api/plan/{pid}/logs", json={
        "log_date": date.today().isoformat(), "distance_m": 3000, "perceived_rpe": 7,
        "notes": "left shoulder tight", "completed_sets": "all"})
    c.post("/api/css", json={"test_date": date.today().isoformat(),
                             "t400_s": 300, "t200_s": 140})
    r = c.post(f"/api/plan/{pid}/next-week")
    assert r.status_code == 200 and len(r.json()["sessions"]) == 4
    prompt = llm.calls[-1]
    assert "left shoulder tight" in prompt and "3000 m" in prompt
    assert "perceived RPE 7" in prompt and "CSS pace 80.0" in prompt
    assert "pace" in prompt.lower() and "cycle-time" in prompt
    weeks = {s["week_number"] for s in c.get(f"/api/plan/{pid}").json()["sessions"]}
    assert weeks == {1, 2}


def test_next_week_without_history_is_rpe_only():
    c, llm, pid = _client()
    assert c.post(f"/api/plan/{pid}/next-week").status_code == 200
    assert "cycle-time" not in llm.calls[-1] and "Recent training logs" not in llm.calls[-1]
