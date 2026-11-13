"""Tool definitions in the Bedrock Messages API tool schema (SERVICE.md tool table)."""


READ_TOOLS = ("search_knowledge", "get_current_plan", "get_css", "list_logs")


WRITE_TOOLS = ("generate_plan", "save_log", "save_css", "generate_next_week")


def _obj(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": properties, "required": required or []}


TOOLS = [
    {"name": "generate_plan",
     "description": "대회일·종목·주간 횟수·세션 시간으로 전체 주기화 계획과 이번 주 세트표를 생성·저장한다.",
     "input_schema": _obj({"competition_date": {"type": "string", "description": "YYYY-MM-DD"},
                           "event": {"type": "string", "description": "예: 200m freestyle"},
                           "sessions_per_week": {"type": "integer"},
                           "session_minutes": {"type": "integer"}},
                          ["competition_date", "event", "sessions_per_week", "session_minutes"])},
    {"name": "save_log", "description": "수행한 훈련 일지를 저장한다.",
     "input_schema": _obj({"log_date": {"type": "string"}, "perceived_rpe": {"type": "number"},
                           "distance_m": {"type": "integer"}, "completed_sets": {"type": "string"},
                           "notes": {"type": "string"}, "plan_id": {"type": "integer"}},
                          ["log_date", "perceived_rpe"])},
    {"name": "list_logs", "description": "저장된 훈련 일지를 조회한다.",
     "input_schema": _obj({"plan_id": {"type": "integer"}})},
    {"name": "save_css",
     "description": "400m·200m 기록을 저장하고 CSS 페이스((T400-T200)/2, 100m당)를 계산한다.",
     "input_schema": _obj({"test_date": {"type": "string"}, "t400_s": {"type": "number"},
                           "t200_s": {"type": "number"}}, ["test_date", "t400_s", "t200_s"])},
    {"name": "generate_next_week", "description": "저장된 일지·CSS를 참고해 다음 주 세트표를 생성·저장한다.",
     "input_schema": _obj({"plan_id": {"type": "integer"}})},
    {"name": "search_knowledge", "description": "수영 코칭 지식베이스를 검색한다(읽기 전용).",
     "input_schema": _obj({"query": {"type": "string"}, "k": {"type": "integer"}}, ["query"])},
    {"name": "get_current_plan", "description": "현재 훈련 계획과 세트표를 조회한다(읽기 전용).",
     "input_schema": _obj({"plan_id": {"type": "integer"}})},
    {"name": "get_css", "description": "저장된 CSS 테스트 결과를 조회한다(읽기 전용).",
     "input_schema": _obj({})},
]


assert {t["name"] for t in TOOLS} == set(READ_TOOLS) | set(WRITE_TOOLS)
