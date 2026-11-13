"""G-03: write tools run only when the user's message explicitly asks for that action."""
import re


INTENT = {
    "generate_plan": re.compile(r"계획.{0,10}(만들|생성|짜|세워|작성)|플랜.{0,10}(만들|생성|짜)|"
                                r"주\s*\d+\s*회.{0,40}?\d+\s*분|"
                                r"(generate|create|make|build)\s+(me\s+)?(a\s+)?(training\s+)?plan",
                                re.I | re.S),
    "generate_next_week": re.compile(r"다음\s*주|next[\s-]*week", re.I | re.S),
    "save_log": re.compile(r"(일지|기록|로그).{0,12}(저장|남겨|추가|기록)|(저장|기록).{0,12}(일지|로그)|"
                           r"(save|record|add|log)\s+(my\s+|a\s+|the\s+)?(training\s+)?(log|session|workout)",
                           re.I | re.S),
    "save_css": re.compile(r"(css|400\s*m|200\s*m).{0,30}(저장|기록)|(저장|기록).{0,20}(css|400|200)|"
                           r"save.{0,20}css", re.I | re.S),
}

_INTENT = INTENT  # backward-compatible name


def has_intent(tool: str, message: str) -> bool:
    return bool(INTENT[tool].search(message or ""))
