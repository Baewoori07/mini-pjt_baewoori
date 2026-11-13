from datetime import date

from tests.test_logs_css_coach import setup


def test_coaching_answer_uses_plan_and_logs_and_keeps_sets_unchanged():
    c, llm, pid = setup()
    c.post(f"/api/plan/{pid}/logs", json={"log_date": date.today().isoformat(),
           "perceived_rpe": 8, "notes": "dropped elbow"})
    c.post("/api/css", json={"test_date": date.today().isoformat(), "t400_s": 300, "t200_s": 140})
    before = c.get(f"/api/plan/{pid}").json()
    calls_before = len(llm.calls)

    r = c.post("/api/coach", json={"message": "Which drills fix my freestyle catch?", "plan_id": pid})

    assert r.status_code == 200
    assert "drill" in r.json()["reply"]
    assert len(llm.calls) == calls_before + 1
    prompt = llm.calls[-1]
    assert "Which drills fix my freestyle catch?" in prompt
    assert "200m freestyle" in prompt          # stored plan
    assert "RPE" in prompt                      # stored set table
    assert "dropped elbow" in prompt            # stored log
    assert "80.0" in prompt                     # stored CSS
    assert c.get(f"/api/plan/{pid}").json() == before  # sets unchanged


def test_coaching_without_plan_and_empty_message():
    c, llm, _ = setup()
    assert c.post("/api/coach", json={"message": "How to breathe bilaterally?"}).status_code == 200
    assert c.post("/api/coach", json={"message": ""}).status_code == 422
