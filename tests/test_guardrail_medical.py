import pytest
from fastapi.testclient import TestClient

from src import coaching as coach
from src.main import create_app


class SpyLLM:
    def __init__(self, reply):
        self.reply = reply
        self.systems = []
        self.prompts = []

    def complete(self, system, prompt):
        self.systems.append(system)
        self.prompts.append(prompt)
        return self.reply


def ask(llm, msg):
    c = TestClient(create_app(llm, ":memory:"))
    r = c.post("/api/coach", json={"message": msg})
    assert r.status_code == 200
    return r.json()["reply"]


@pytest.mark.parametrize("msg", [
    "My shoulder pain gets worse during freestyle, what drills help?",
    "I have a knee injury from breaststroke kick",
    "어깨가 아픈데 접영 드릴 알려줘",
    "팔꿈치 통증이 있어요",
])
def test_pain_question_gets_safety_system_prompt_and_notice(msg):
    llm = SpyLLM("Try fingertip drag drill and take ibuprofen 400mg.")  # model omits notice
    reply = ask(llm, msg)
    s = llm.systems[-1].lower()
    assert "stop training" in s and "medical specialist" in s
    assert "not name any medication or dosage" in s
    assert "not diagnose" in s
    assert "not recommend raising" in s
    assert "specialist" in reply.lower() or "전문" in reply
    assert ("stop training" in reply.lower()) or "중단" in reply


def test_notice_not_duplicated_and_not_added_without_pain():
    llm = SpyLLM("Keep your elbow high.")
    reply = ask(llm, "How do I improve my catch?")
    assert reply == "Keep your elbow high."
    assert "medical specialist" not in llm.systems[-1]

    llm2 = SpyLLM("x")
    r = ask(llm2, "My wrist hurts")
    assert r.count(coach.NOTICE_EN) == 1
    llm3 = SpyLLM("x " + coach.NOTICE_EN)
    assert ask(llm3, "My wrist hurts").count(coach.NOTICE_EN) == 1
