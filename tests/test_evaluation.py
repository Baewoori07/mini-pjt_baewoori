"""Evaluation harness end-to-end with mocked app and judge clients (never calls Bedrock)."""
import json
from types import SimpleNamespace

from evaluation import cases as cases_mod
from evaluation import metrics, report
from evaluation.run import run_round


def text(t):
    return SimpleNamespace(type="text", text=t)


def call(name, **inp):
    return SimpleNamespace(type="tool_use", id="t1", name=name, input=inp)


def resp(*b):
    return SimpleNamespace(content=list(b), usage=SimpleNamespace(input_tokens=10, output_tokens=5))


class MockApp:
    """First turn: search_knowledge for coaching questions, otherwise answer directly."""

    def __init__(self, fail_ids=()):
        self.calls = 0

    def chat(self, system, messages, tools):
        self.calls += 1
        last = messages[-1]
        if isinstance(last["content"], str) and ("드릴" in last["content"] or "목적" in last["content"]):
            return resp(call("search_knowledge", query="하이엘보 캐치 드릴"))
        return resp(text("답변입니다. 하이엘보 캐치는 팔꿈치를 높게 유지하는 것입니다."))

    def complete(self, system, prompt):
        return "{}"


class MockJudge:
    def __init__(self, verdict="pass"):
        self.verdict, self.tasks = verdict, []

    def complete(self, system, prompt):
        task = prompt.split("\n", 1)[0].removeprefix("TASK: ")
        self.tasks.append(task)
        out = {
            "judge": {"verdict": self.verdict, "score": 4, "reason": "충족"},
            "faithfulness_claims": {"claims": ["a", "b"]},
            "faithfulness_verdicts": {"verdicts": [1, 0]},
            "answer_relevancy": {"questions": [{"q": "x", "similarity": 0.8},
                                               {"q": "y", "similarity": 0.6}],
                                 "noncommittal": False},
            "context_precision": {"relevant": [1, 0, 1]},
            "context_recall": {"attributed": [1, 0]},
        }[task]
        return "```json\n" + json.dumps(out) + "\n```"


def test_cases_load_and_prepare(tmp_path):
    from src.shared import db
    from src.css_test import repository as css_repo
    from src.training_log import repository as log_repo
    cs = cases_mod.load_cases()
    assert len(cs) == 16 and {c.category for c in cs} == {"positive", "negative", "edge", "guardrail"}
    conn = db.connect(str(tmp_path / "t.db"))
    assert cases_mod.prepare(conn, cs[3]) == 1  # case 4: plan + log + css
    assert log_repo.list_logs(conn, 1) and css_repo.list_css(conn)
    conn2 = db.connect(str(tmp_path / "t2.db"))
    pid = cases_mod.prepare(conn2, cs[8])      # case 9: plan with empty logs
    assert log_repo.list_logs(conn2, pid) == []
    conn3 = db.connect(str(tmp_path / "t3.db"))
    pid = cases_mod.prepare(conn3, cs[14])     # case 15: injected log text
    assert "SYSTEM" in log_repo.list_logs(conn3, pid)[0]["notes"]


def test_ragas_math():
    from evaluation.cases import Case
    judge = MockJudge()
    c = Case(5, "positive", "q", ["a", "b"], [], [], "")
    assert metrics.faithfulness(judge, "q", "ans", ["ctx"]) == 0.5
    assert abs(metrics.answer_relevancy(judge, "q", "ans") - 0.7) < 1e-9
    assert abs(metrics.context_precision(judge, "q", c, ["1", "2", "3"]) - (1 + 2 / 3) / 2) < 1e-9
    assert metrics.context_recall(judge, c, ["ctx"]) == 0.5


def test_tool_match():
    from evaluation.cases import Case
    c = Case(1, "positive", "q", [], [], ["generate_plan"], "")
    ok = {"tool_calls": [{"name": "generate_plan", "is_error": False}]}
    assert metrics.tool_match(c, ok)["match"]
    assert metrics.tool_match(c, {"tool_calls": []})["missing"] == ["generate_plan"]
    c2 = Case(13, "edge", "q", [], [], ["coach_chat"], "")
    bad = {"tool_calls": [{"name": "search_knowledge"}, {"name": "generate_plan", "is_error": False}]}
    assert metrics.tool_match(c2, bad)["unexpected_writes"] == ["generate_plan"]
    assert metrics.tool_match(c2, {"tool_calls": [{"name": "search_knowledge"}]})["match"]


def test_round_end_to_end_and_comparison(tmp_path):
    app, judge = MockApp(), MockJudge()
    data = run_round(1, app, judge, out_dir=tmp_path, meta={"app_model": "m", "judge_model": "j"})
    assert (tmp_path / "round1_results.json").exists()
    rep = (tmp_path / "round1_report.md").read_text(encoding="utf-8")
    for head in ("전체 통과율", "가드레일 통과율", "카테고리별", "RAGAS", "케이스별", "실패 분석"):
        assert head in rep
    s = data["summary"]
    assert s["total"] == 16 and s["ragas_cases"] >= 1 and s["avg_tokens"] is not None
    assert set(s["by_category"]) == {"positive", "negative", "edge", "guardrail"}
    # case 7/8/16 are refused/handled by guardrails before the model; case 1 needs generate_plan
    by_id = {r["id"]: r for r in data["cases"]}
    assert by_id[1]["tool_match"]["missing"] == ["generate_plan", "validate_duration"] or \
        "generate_plan" in by_id[1]["tool_match"]["missing"]
    assert not by_id[1]["passed"] and "개선 제안" in rep
    assert by_id[5]["ragas"] is not None and by_id[5]["passed"]
    assert by_id[16]["passed"]
    assert list((tmp_path / "traces" / "round1").glob("*.jsonl"))
    assert "이전 라운드 결과가 없어" in rep

    run_round(2, app, MockJudge("fail"), out_dir=tmp_path)
    rep2 = (tmp_path / "round2_report.md").read_text(encoding="utf-8")
    assert "라운드 1 → 라운드 2" in rep2 and "회귀" in rep2
    assert json.loads((tmp_path / "round2_results.json").read_text(encoding="utf-8"))["round"] == 2


def test_secret_leak_forces_fail(monkeypatch):
    from evaluation.cases import Case
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "SUPERSECRETVALUE123")
    assert metrics.leaked_secret("key SUPERSECRETVALUE123")
    c = Case(16, "guardrail", "q", [], [], [], "")
    j = metrics.judge_case(MockJudge(), c, "x", {}, secret_leak=True)
    assert j["verdict"] == "fail" and "SUPERSECRETVALUE123" not in j["reason"]


def test_summarize_empty_ragas():
    s = report.summarize([{"category": "negative", "passed": True, "judge": {"verdict": "pass"},
                           "tool_match": {"match": True}, "ragas": None, "latency_ms": 1.0,
                           "tokens": {"input": 1, "output": 1, "total": 2}}])
    assert s["ragas_avg"]["faithfulness"] is None and s["overall_pass_rate"] == 1.0
