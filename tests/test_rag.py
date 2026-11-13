from pathlib import Path

import pytest

from src import coaching as coach
from src import knowledge as retriever
KDIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"


def test_at_least_15_korean_docs_with_titles():
    docs = list(KDIR.glob("*.md"))
    assert len(docs) >= 15
    for d in docs:
        t = d.read_text(encoding="utf-8")
        assert t.startswith("# ") and any("가" <= ch <= "힣" for ch in t)


@pytest.mark.parametrize("query,doc", [
    ("하이엘보 캐치", "freestyle_catch"),
    ("자유형 캐치할 때 팔꿈치가 떨어져요", "freestyle_catch"),
    ("CSS", "css_test"),
    ("CSS 페이스 계산식", "css_test"),
    ("테이퍼 어떻게 하나요", "taper"),
    ("RPE가 뭐예요", "rpe"),
    ("평영 킥 발목", "breaststroke"),
    ("접영 웨이브 돌핀킥", "butterfly"),
    ("플립 턴 요령", "turns"),
    ("출발 다이브 입수", "starts"),
    ("주기화 기초기 강화기", "periodization"),
    ("어깨 부상 예방", "injury_prevention"),
    ("배영 롤링", "backstroke"),
])
def test_expected_doc_in_top3(query, doc):
    hits = retriever.search_knowledge(query, k=3)
    assert doc in [h["doc_id"] for h in hits]
    assert all(h["title"] and h["text"] for h in hits)


def test_unrelated_query_returns_nothing():
    assert retriever.search_knowledge("zzzz qqqq", k=3) == []


class Echo:
    def __init__(self):
        self.prompts = []

    def complete(self, system, prompt):
        self.prompts.append(prompt)
        return "답변입니다"


def test_coaching_answer_cites_source_titles_and_uses_context():
    llm = Echo()
    out = coach.answer(llm, "하이엘보 캐치 드릴 알려주세요", None, [], [], [])
    assert "출처:" in out and "자유형 하이엘보 캐치" in out
    assert "Knowledge base excerpts" in llm.prompts[0]
