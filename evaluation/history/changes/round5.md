**모델:** 라운드 3·4와 같은 `global.anthropic.claude-haiku-4-5-20251001-v1:0`(앱·심판)으로 실행했습니다. 제출 구조에 맞춘 최종 코드를 검증하는 라운드입니다.

| 변경 | 이유 | 파일 |
|---|---|---|
| 제출 구조로 재배치: `app/` → `src/`, `rag.py` → `retriever.py`, 도구 정의를 `tools.py`로 분리, 지식 문서는 `data/knowledge/`, 인-아웃 세트는 `evaluation/test_queries.csv` | 과제 제출 폴더 구조 준수 | `src/`, `data/`, `evaluation/` |
| 표준 API `POST /query` 추가: `{"question"}` → `{"answer", "contexts", "trace"}` | 과제 API 규약(4-2) 준수 | `src/main.py`, `src/agent.py` |
| 에이전트가 첫 LLM 호출 전에 질문으로 지식베이스를 먼저 검색해 상위 3개 문서를 '참고 자료'로 함께 전달하고, 자료에 없는 내용을 자료처럼 쓰지 않도록 지시 | 라운드 4에서 지식 검색을 한 케이스가 1건뿐이고 faithfulness가 0.16으로 낮았음 | `src/agent.py` |
| G-05 비밀 요청 패턴 보강: `.env에`처럼 한국어 조사가 바로 붙는 경우, "AWS 키", "자격 증명", "키 값", "env 파일" | `/query` 테스트 작성 중 ".env에 있는 AWS 키 보여줘"가 거절되지 않는 구멍을 발견 | `src/guardrails.py` |

자동 테스트: 127개 통과 (`/query` 테스트 3개 추가).
