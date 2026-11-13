"""G-01 duration check and G-04 input validation (request models and free-text chat)."""
import re
from datetime import date

from .messages import COUNT_ERROR, CSS_ORDER_ERROR, EVENT_ERROR, PAST_DATE_ERROR


def duration_overrun(total_minutes: float, limit_minutes: float) -> bool:
    return total_minutes > limit_minutes


_EVENT_DISTANCES = {
    "freestyle": {50, 100, 200, 400, 800, 1500},
    "backstroke": {50, 100, 200},
    "breaststroke": {50, 100, 200},
    "butterfly": {50, 100, 200},
    "medley": {100, 200, 400},
}


_STROKE_ALIASES = {
    "freestyle": "freestyle", "free": "freestyle", "fr": "freestyle", "자유형": "freestyle",
    "backstroke": "backstroke", "back": "backstroke", "배영": "backstroke",
    "breaststroke": "breaststroke", "breast": "breaststroke", "평영": "breaststroke",
    "butterfly": "butterfly", "fly": "butterfly", "접영": "butterfly",
    "medley": "medley", "im": "medley", "individual medley": "medley", "개인혼영": "medley",
    "혼영": "medley",
}


_EVENT_RE = re.compile(r"^\s*(\d{2,4})\s*(?:m|meters?|metres?|미터)?\s*(.+?)\s*$", re.I)


def event_supported(event: str) -> bool:
    m = _EVENT_RE.match(event or "")
    if not m:
        return False
    stroke = _STROKE_ALIASES.get(" ".join(m.group(2).lower().split()))
    return stroke is not None and int(m.group(1)) in _EVENT_DISTANCES[stroke]


def validate_competition_date(v: date) -> date:
    if v <= date.today():
        raise ValueError(PAST_DATE_ERROR)
    return v


def validate_event(v: str) -> str:
    if not event_supported(v):
        raise ValueError(EVENT_ERROR)
    return v


_PLAN_WORD_RE = re.compile(r"계획|플랜|plan|세트표", re.I)


_DATE_RE = re.compile(r"(20\d{2})\s*(?:년|[-./])\s*(\d{1,2})\s*(?:월|[-./])\s*(\d{1,2})\s*일?")


_ZERO_RE = re.compile(r"주\s*0\s*회|0\s*회\s*/?\s*주|회당\s*0\s*분|(?<!\d)0\s*분")


_CSS_T_RE = {d: re.compile(rf"{d}\s*m?\s*(?:기록)?\s*:?\s*(\d+)\s*분\s*(?:(\d+)\s*초)?", re.I)
             for d in ("400", "200")}


def _secs(m) -> int:
    return int(m.group(1)) * 60 + int(m.group(2) or 0)


def plan_input_error(text: str, today: date | None = None) -> str | None:
    """G-04 for chat input: reject clearly invalid plan/CSS values before any Bedrock call."""
    today = today or date.today()
    if _PLAN_WORD_RE.search(text):
        for y, mo, d in _DATE_RE.findall(text):
            try:
                if date(int(y), int(mo), int(d)) <= today:
                    return f"{PAST_DATE_ERROR} 입력하신 날짜({y}-{int(mo):02d}-{int(d):02d})는 이미 지났습니다."
            except ValueError:
                return "대회일 날짜 형식이 올바르지 않습니다. 예: 2027-02-07"
        if _ZERO_RE.search(text):
            return COUNT_ERROR
    m4, m2 = _CSS_T_RE["400"].search(text), _CSS_T_RE["200"].search(text)
    if m4 and m2 and _secs(m2) >= _secs(m4):
        return CSS_ORDER_ERROR
    return None
