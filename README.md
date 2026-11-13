# 미니 PJT: SwimCoach (마스터즈 수영 훈련 코치 에이전트)

## 무엇을 푸나
코치 없이 혼자 대회를 준비하는 상급 동호인 수영인이 "대회까지 언제, 무엇을, 얼마나 세게" 해야 하는지 몰라 훈련이 그날 기분에 따라 흔들리는 문제를, 대회일 기준 주기화 계획과 세션 시간 안에 들어오는 세트표, 일지 기반 다음 주 조정, 근거 기반 기술 코칭으로 해결합니다. (자세한 기획: [SERVICE.md](SERVICE.md))

## 활용한 패턴 (Day 1~7)
실습은 LangChain·LangGraph로 진행했지만, 이 프로젝트는 처음 정한 조건(LangChain·LangSmith 미사용)에 따라 **Anthropic SDK(AnthropicBedrock)를 직접 호출하면서 같은 패턴을 직접 구현**했습니다.

- **Day 1: LLM 호출·구조화 출력·도구 호출 결정·멀티턴** — 세트표를 JSON 구조로 받아 코드로 검증(`src/training_plan/`), 대화 기록 최근 10턴 유지, Bedrock Messages API의 `tools`로 모델이 도구 호출을 결정, 토큰 사용량 기록
- **Day 2: RAG (마크다운 청킹·BM25·출처 검증·환각 방지)** — `data/knowledge/` 지식 문서 16개를 `## ` 섹션 단위로 청킹(34개)하고 한국어 BM25로 검색(`src/knowledge/retriever.py`), 답변 끝에 '참고:' 출처 표기, "자료에 없는 내용을 자료처럼 쓰지 말 것" 규칙
- **Day 3: ReAct 루프 직접 구현 (manual_react)** — `src/agents/runner.py`의 `run_agent`가 입력 검사 → 사전 검색 → [LLM ↔ 도구]* (최대 8단계) → 출력 검사로 이어지는 에이전트 그래프를 while 루프로 구현
- **Day 4: 도구 정의·도구 오류 복구·실행 추적** — 도구 9개를 스키마로 정의(`src/agent_tools/`), 도구 예외를 `is_error` 결과로 모델에 돌려 스스로 복구하게 함, 쓰기 도구는 사용자 명시 의도가 있을 때만 실행(G-03)
- **Day 5: 입력·출력 가드레일·고정 거절 문구·마스킹·공격 세트** — G-01~G-05를 `src/guardrails/` 도메인 한 곳에 모아 에이전트 전후로 적용, 한국어 고정 거절 문구, AWS 자격증명 값 마스킹(`redact`), 일지를 통한 프롬프트 인젝션 케이스 검증
- **Day 6: 에이전트를 API로 노출 (FastAPI)** — 표준 API `POST /query`, 계획·일지·CSS REST API (도메인별 `router.py`, 앱 조립은 `src/main.py`), 웹 화면(`static/index.html`: 오른쪽 수영 프로그램 패널, 버튼으로 여는 프로그램 생성·훈련 기록·CSS 입력 창, 코치 채팅 패널)
- **Day 7: 로컬 트레이서·LLM 심사·누적 평가셋 실행** — 요청마다 JSONL 트레이스(`src/shared/tracing.py`), 고정 루브릭 LLM-as-Judge와 RAGAS 4지표 자체 구현(`evaluation/metrics.py`), 라운드별 리포트 자동 생성(`evaluation/run.py`)

## 아키텍처

```
사용자 (웹 화면 / POST /query / POST /api/chat)
   │
   ▼
src/main.py  FastAPI (도메인 router 조립) ─────────── traces/*.jsonl (src/shared/tracing.py)
   │                                                      ▲ LLM 호출·도구 호출·검색 청크·가드레일 판정·지연·토큰
   ▼
src/agents/runner.py  run_agent (에이전트 그래프)
   ① guardrail_input   src/guardrails/       G-02 통증 감지 · G-03 세트표 수정 요청 · G-04 잘못된 입력 · G-05 비밀/주제 외
   ② retrieve          src/knowledge/        질문으로 BM25 상위 3개 → '참고 자료'로 첫 메시지에 첨부
   ③ llm ⇄ tools       Claude (Bedrock)  ⇄  src/agent_tools/
        읽기: search_knowledge · get_current_plan · get_css · list_logs
        쓰기: generate_plan · generate_next_week · save_log · save_css   (명시 요청 시에만)
              └ src/training_plan/service.py: 세트표 JSON 생성 → validate_duration(세션 시간 검사) → 초과 시 최대 2회 재생성 → 경고 (G-01)
   ④ guardrail_output  비밀 값 마스킹 · 의료 안내 · 세트표 미수정 안내
   │
   ▼
{"answer", "contexts": [{doc_id, text}], "trace": [{step, input, output}]}
```

- **데이터:** SQLite(`data/swim.db`)에 계획·주차·세션·일지·CSS·대화 저장
- **모델:** 기본 `global.anthropic.claude-sonnet-4-6` (계정에 Sonnet 5.5 없음). `BEDROCK_MODEL_ID`로 변경

## 실행 방법

```bash
# 0) 준비: .env 에 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION (Bedrock 사용 권한)
# 1) 설치
uv sync                              # 또는: pip install -r requirements.txt
# 2) 서버 실행 → http://127.0.0.1:8000 (웹 화면), POST /query (표준 API)
./run.sh serve                       # = uv run uvicorn src.main:create_app --factory --port 8000
# 3) 자동 테스트 (Bedrock 모킹, 실제 호출 없음, 133개)
./run.sh test
# 4) 자체 평가 라운드 N (evaluation/test_queries.csv 16건, 실제 Bedrock 호출)
./run.sh eval 3
# 모델 변경 예: BEDROCK_MODEL_ID=global.anthropic.claude-haiku-4-5-20251001-v1:0 JUDGE_MODEL_ID=... ./run.sh eval 3
```

```bash
curl -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" \
     -d '{"question": "자유형 캐치할 때 팔꿈치가 떨어져요. 드릴 알려주세요."}'
```

Docker(선택): `docker build -t swimcoach .` → `docker run --rm -p 8000:8000 --env-file .env swimcoach` (작성 PC에 Docker가 없어 빌드는 검증하지 못했습니다)

## RAGAS 평가 결과
2차 자체 평가(실제 라운드 6, 앱·심판 Haiku 4.5) 기준, 지식 검색을 한 12건의 평균입니다. 4개 지표 모두 RAGAS 정의에 따라 심판 LLM으로 직접 구현했습니다(`evaluation/metrics.py`, ragas 패키지 미사용).

- context_recall: 0.38
- context_precision: 0.54
- faithfulness: 0.29
- answer_relevancy: 0.82

**해석:** faithfulness가 낮은 이유는 두 가지입니다.
1. **지표 구조:** 계획 생성·다음 주 생성 답변(케이스 1·4·11·15: 0.0~0.28)은 지식 문서가 아니라 **도구 결과(생성된 세트표, 저장된 일지)**에 근거하는데, faithfulness는 검색된 지식 문서만 근거로 봅니다.
2. **모델이 자료 밖 지식을 섞음:** 순수 기술 코칭 질문(케이스 5)도 0.45에 그쳤습니다. 검색 정밀도는 0.92로 높았는데도 답변의 절반 정도가 검색 자료에 없는 일반 지식이었습니다. 가장 높은 것은 CSS 계산 안내(케이스 2, 0.86)였습니다.

context_precision·recall이 0인 케이스(6·10·13·15)는 계획 조회나 세트표 관련 질문이어서, 지식 문서 중에 정답 근거가 없는 경우입니다.

## 인-아웃 세트 통과율 (자체 평가)
기준: `evaluation/test_queries.csv` 16건. 통과 = LLM 심판 pass **그리고** 기대 도구 일치.

- 1차 (Day 9 종료): 6 / 16 통과 (37.5%, 가드레일 2/3) — 실제 라운드 3, [round1_report.md](evaluation/round1_report.md)
- 2차 (Day 10 개선 후): 14 / 16 통과 (87.5%, 가드레일 3/3) — 실제 라운드 6, [round2_report.md](evaluation/round2_report.md)
- 개선폭: +8 건 (주요 개선 사항: 심판에 오늘 날짜·사전 데이터·도구 결과를 제공해 오판 제거, 에이전트 규칙 보강(계획 ID 되묻지 않기·계획 입력 인식·저장 후 안내·세트표 출력 형식), 매 질문 지식 사전 검색, G-04 입력 사전 검사, G-05 패턴 보강)

목표(전체 90%·가드레일 100%) 중 가드레일은 달성했고, 전체는 1건 차이로 미달입니다. 실제로는 라운드 6번을 실행했으며 전체 이력은 [evaluation/history/](evaluation/history/README.md)에 있습니다.

## 트라이앤에러 회고
- **시도했지만 실패한 접근 · 왜 실패했는가**
  - *Sonnet으로 평가 반복:* 라운드 1은 SDK 기본 재시도만으로 돌려 16건 중 9건이 요청 한도(429)로 빈 응답이었습니다. 재시도를 8회로 늘린 라운드 2는 실행 중 **일일 토큰 한도**가 소진돼 무효가 됐습니다. 그래서 라운드가 한도에 걸리면 즉시 중단하도록 하고, 이후 라운드는 Haiku 4.5로 진행했습니다.
  - *세트표 수정 요청을 고정 문구로 거절:* 안전하지만 사용자가 원한 "강도 조절 방법"을 주지 못해 실패했습니다. 거절 대신 읽기 전용 규칙을 붙여 텍스트로만 조정 방법을 제안하도록 바꿨습니다.
  - *심판에게 질문과 답변만 주기:* 심판이 오늘 날짜도, 미리 저장된 일지·계획도, 도구 결과도 몰라서 정확한 인용을 "지어냈다"고 판정하는 등 오판이 절반이었습니다.
  - *RAG를 도구로만 제공:* 모델이 검색 도구를 거의 부르지 않아 RAGAS가 16건 중 1건만 계산됐습니다.
- **최종 채택한 접근 · 왜 그것으로 갔는가**
  - *직접 구현한 ReAct 루프 + 쓰기 도구 의도 게이트:* 프레임워크 없이도 단계 수, 도구 오류 복구, 트레이스를 완전히 통제할 수 있었고, 코칭 질문이 세트표를 바꾸는 사고를 코드로 막을 수 있었습니다.
  - *가드레일은 모델이 아니라 코드로:* G-04 입력 검증, G-05 비밀 값 마스킹, 의료 안내문 강제 추가를 코드에서 처리해 모델이 놓쳐도 지켜지게 했습니다(가드레일 케이스 3/3).
  - *매 질문 사전 검색:* 도구 호출 여부와 관계없이 관련 문서를 근거로 붙여 RAGAS를 12건에서 산출하고, `/query`의 `contexts`를 항상 채웠습니다.
  - *심판에 근거 제공:* 날짜·사전 데이터·도구 결과를 주자 심판 통과율이 56%에서 94%로 올라갔습니다. 다만 이 중 일부는 앱 개선이 아니라 채점 보정입니다.
- **남은 한계 · 향후 개선 방향**
  - *케이스 4:* 다음 주 생성 도구가 돌려준 세트표 대신 에이전트가 숫자가 다른 세트표를 다시 써서 보여 줍니다. 도구 결과를 그대로 옮기도록 강제하거나, 세트표를 코드가 직접 렌더링하는 방향이 필요합니다.
  - *케이스 10:* 입력에 대회일이 없어 `generate_plan`을 기대할 수 없는 테스트셋 문제입니다. 테스트셋 보정이 필요합니다.
  - *심판 모델:* Day 7 원칙("버전 비교는 같은 judge로")과 달리 한도 문제로 심판이 Sonnet에서 Haiku로 바뀌었고, 앱과 심판이 같은 모델이라 자기 평가 편향이 있을 수 있습니다. 운영 모델인 Sonnet 4.6으로는 아직 재검증하지 못했습니다.
  - *faithfulness (0.29):* 도구 결과도 근거(contexts)로 포함하도록 지표를 확장하고, 코칭 답변은 검색 자료 안에서만 답하도록 더 강하게 제한하며, 지식 문서를 늘려 검색 재현율을 높여야 합니다.
  - *지식 문서:* 앱을 위해 직접 작성한 일반 코칭 지식이며 외부 검증 출처가 아닙니다. 16건 1회 실행이라 실행마다 ±1~2건 변동이 있습니다.

## 핵심 코드 위치
> 제출 규격의 `src/agent.py`·`src/tools.py`·`src/retriever.py`는 아래 도메인 폴더를 다시 내보내는 진입점입니다.

- `src/agents/runner.py:52` — 메인 에이전트 그래프 (`run_agent`: 입력 가드레일 → 사전 검색 → LLM ⇄ 도구 → 출력 가드레일), 프롬프트 `src/agents/prompts.py`
- `src/agent_tools/` — 도메인 도구 (`TOOLS` 스키마 `schemas.py:14`, 실행기 `ToolContext` `executor.py:16`, 쓰기 의도 게이트 `INTENT` `intent.py:5`)
- `src/knowledge/retriever.py` — RAG 파이프라인 (청킹 `load_chunks` `:30`, `BM25Index` `:44`, `search_knowledge` `:82`)
- `src/guardrails/` — 가드레일 G-01~G-05 (`check_input` `policy.py:68`, `check_output` `policy.py:96`, 입력 검증 `validators.py`, 거절 문구 `messages.py`)
- `src/shared/tracing.py:121` — JSONL 트레이스 (`request_trace`)
- `src/agents/router.py:27` — 표준 API `POST /query`
- `src/training_plan/service.py` — 세트표 생성 + 세션 시간 검사·최대 2회 재생성
- `evaluation/run.py`, `evaluation/metrics.py` — 자체 평가 (LLM-as-Judge `judge_case` `:44`, 도구 일치 `tool_match` `:70`, RAGAS `ragas` `:178`)

## 폴더 구조
```
src/            도메인별 폴더 (규칙은 AGENTS.md)
  agents/         에이전트 루프 · 프롬프트 · /api/chat, /query
  agent_tools/    도구 스키마 · 쓰기 의도 게이트 · 실행기
  knowledge/      RAG (BM25 검색)
  guardrails/     G-01~G-05
  training_plan/  주기화 계획 · 세트표 생성 · 재생성
  training_log/   훈련 일지
  css_test/       CSS 측정
  memory/         대화 기록
  coaching/       텍스트 코칭 /api/coach
  shared/         LLM 클라이언트 · 트레이싱 · 마스킹 · DB 연결 · 웹 의존성
  main.py         앱 조립 / agent.py · tools.py · retriever.py 제출 규격 진입점
static/         웹 화면 (index.html)
data/knowledge/ RAG 지식 문서 16개 (직접 작성)
evaluation/     test_queries.csv · round1_report.md · round2_report.md · 평가 하네스(run.py, metrics.py, cases.py, report.py) · history/
tests/          자동 테스트 133개 (Bedrock 모킹)
SERVICE.md · README.md · requirements.txt · pyproject.toml · run.sh · Dockerfile
```
