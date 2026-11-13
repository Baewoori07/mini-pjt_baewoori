# SwimCoach — `src/` 구조 규칙

모든 소스 코드는 `src/` 아래에 두고, **기술 역할(utils, models…)이 아니라 도메인(기능) 단위**로 폴더를 나눈다.
이 규칙은 `tests/test_structure.py`가 검사한다. 규칙을 바꾸면 테스트도 함께 바꾼다.

## 폴더 역할

| 폴더 | 도메인 | 담당 |
|---|---|---|
| `src/agents/` | 코치 에이전트 | 도구 호출 루프 `run_agent` (입력 가드레일 → 사전 검색 → LLM ⇄ 도구 최대 8단계 → 출력 가드레일), `POST /api/chat`, `POST /query` |
| `src/agent_tools/` | 에이전트 도구 | 도구 9개의 스키마, 쓰기 도구 의도 게이트(G-03), 도구 실행기 `ToolContext` |
| `src/knowledge/` | 지식 검색(RAG) | `data/knowledge/*.md` 청킹, BM25 검색, 검색 결과 표시·출처 문구 |
| `src/guardrails/` | 가드레일 | G-01~G-05: 입력 검사·출력 검사(`policy.py`), 입력 검증(`validators.py`), 거절·안내 문구와 안전 규칙 프롬프트(`messages.py`) |
| `src/training_plan/` | 훈련 계획 | 주기화(기초→강화→테이퍼), 세트표 생성, 세션 시간 초과 시 최대 2회 재생성 |
| `src/training_log/` | 훈련 일지 | 수행 기록 저장·조회 (다음 주 생성에 반영) |
| `src/css_test/` | CSS 측정 | 400m·200m 기록 → CSS 페이스 계산·저장 |
| `src/memory/` | 대화 기록 | 채팅 이력 저장·조회 (에이전트와 텍스트 코치가 함께 사용) |
| `src/coaching/` | 텍스트 코칭 | 도구 없는 질의응답 `POST /api/coach` |
| `src/shared/` | 공통 인프라 | LLM 클라이언트(`llm.py`), 트레이싱(`tracing.py`), 자격 증명 마스킹(`redaction.py`), DB 연결·전체 스키마(`db.py`), FastAPI 의존성(`web.py`) |
| `src/main.py` | 앱 조립 | 도메인 라우터 등록, 정적 파일, `PlanNotFound` → 404 |
| `src/agent.py` · `src/tools.py` · `src/retriever.py` | 제출 규격 진입점 | 과제 규격(4-1)이 요구하는 파일. `agents/` · `agent_tools/` · `knowledge/`를 **다시 내보내기만** 한다 |

## 도메인 폴더 안의 파일 배치

필요한 파일만 둔다. 이름은 아래로 통일한다.

| 파일 | 넣는 것 |
|---|---|
| `__init__.py` | 도메인의 공개 API (다른 도메인이 쓰는 이름만 다시 내보냄) |
| `service.py` / `runner.py` / `policy.py` | 실행 로직 (에이전트 루프는 `runner.py`, 가드레일 판정은 `policy.py`) |
| `prompts.py` | 시스템 프롬프트, 프롬프트 템플릿, 모델에게 보여 줄 텍스트 형식 |
| `schemas.py` | 입출력 타입: Pydantic 요청 모델, TypedDict, 도메인 예외, 열거 상수 |
| `repository.py` | 그 도메인 테이블에 대한 SQL (연결과 `CREATE TABLE`은 `shared/db.py`) |
| `router.py` | FastAPI 라우트. 얇게 유지하고 로직은 service로 보낸다 |
| `messages.py` | 사용자에게 보이는 한국어 고정 문구 (가드레일 등) |

## 의존 규칙

1. `shared/`는 어떤 도메인도 import하지 않는다. 도메인 → `shared` 방향만 허용한다.
2. `router.py`는 `main.py`만 import한다. 다른 도메인의 기능이 필요하면 그 도메인의 `service` · `repository` · `schemas` 또는 `__init__`을 쓴다.
3. 라우터에서 HTTP 오류로 바꿔야 하는 도메인 오류는 `schemas.py`에 예외로 정의하고 `main.py`에서 상태 코드로 바꾼다 (예: `PlanNotFound` → 404).
4. 진입점 파일(`agent.py`, `tools.py`, `retriever.py`)에는 import만 둔다. 로직을 넣지 않는다.
5. 새 기능을 추가할 때는 어느 도메인에 속하는지 먼저 정하고, 맞는 도메인이 없을 때만 새 도메인 폴더를 만든다(위 표와 `tests/test_structure.py`의 `DOMAINS`도 갱신). 여러 도메인이 함께 쓰는 LLM 설정·유틸리티만 `shared/`에 둔다.
6. 사용자 입력, 모델 출력, 트레이스, DB 저장 값은 `shared.redaction.redact`를 거친다.
