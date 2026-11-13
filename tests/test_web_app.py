from datetime import date

from fastapi.testclient import TestClient

from src.main import create_app
from tests.test_logs_css_coach import setup


def test_index_served_without_login_and_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    c = TestClient(create_app(None, ":memory:"))
    r = c.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    html = r.text
    assert "<script>" in html and "login" not in html.lower()
    assert "Authorization" not in html


def test_page_has_all_ui_sections():
    html = TestClient(create_app(None, ":memory:")).get("/").text
    for needle in ['id="f"', 'name="competition_date"', 'name="event"', 'name="sessions_per_week"',
                   'name="session_minutes"', 'id="plan"', 'id="sessions"', 'id="logs"',
                   'id="chat"', 'id="cq"', 'id="nw"', 'id="css"', "/api/plan", "/api/coach"]:
        assert needle in html, needle


def test_static_assets_mounted():
    c = TestClient(create_app(None, ":memory:"))
    assert c.get("/static/index.html").status_code == 200


def test_api_calls_used_by_page_work_end_to_end_without_auth():
    c, llm, pid = setup()
    plan = c.get(f"/api/plan/{pid}").json()
    assert plan["weeks"] and plan["sessions"] and plan["sessions"][0]["sets"]
    c.post(f"/api/plan/{pid}/logs", json={"log_date": date.today().isoformat(),
                                          "perceived_rpe": 6, "distance_m": 2000})
    assert len(c.get(f"/api/plan/{pid}/logs").json()) == 1
    r = c.post("/api/coach", json={"message": "How to improve catch?", "plan_id": pid})
    assert r.status_code == 200 and r.json()["reply"]
    assert c.get("/api/coach/history", params={"plan_id": pid}).status_code == 200


def test_latest_plan_endpoint_restores_page_state():
    c = TestClient(create_app(None, ":memory:"))
    assert c.get("/api/plans/latest").json() == {"id": None}
    c2, _, pid = setup()
    assert c2.get("/api/plans/latest").json() == {"id": pid}
