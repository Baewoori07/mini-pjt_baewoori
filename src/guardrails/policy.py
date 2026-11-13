"""Input check (before the agent loop) and output check (after it): G-02, G-03, G-05."""
import re

from ..shared import tracing
from ..shared.redaction import redact
from .messages import (MEDICAL_NOTICE, MEDICAL_RULES, OFF_TOPIC_REFUSAL, PLAN_EDIT_RULES,
                       SECRET_REFUSAL, SET_EDIT_NOTICE)
from .schemas import InputVerdict
from .validators import plan_input_error


_SECRET_REQUEST_RE = re.compile(
    r"system\s*prompt|system\s*message|시스템\s*프롬프트|시스템\s*메시지|\.env(?![A-Za-z0-9_])|dotenv|"
    r"env\s*파일|aws\s*(키|자격|비밀|계정\s*정보)|(api|액세스|시크릿|secret)\s*키|키\s*값|자격\s*증명|"
    r"aws[\s_-]*(access|secret|key|cred)|secret[\s_-]*(access[\s_-]*)?key|access[\s_-]*key|"
    r"api[\s_-]*key|credential|environment\s*variable|환경\s*변수|비밀\s*키|액세스\s*키|"
    r"(ignore|disregard|forget).{0,30}(previous|above|prior).{0,20}instruction|"
    r"(reveal|show|print|repeat|leak).{0,30}(your|the)\s+(instructions|prompt)|"
    r"이전\s*지시.{0,10}무시",
    re.I | re.S,
)


_OFF_TOPIC_RE = re.compile(
    r"\b(python|javascript|java|c\+\+|sql|code|coding|program(ming)?|script|bug fix|recipe|cook(ing)?|"
    r"stock|stocks|bitcoin|crypto|invest(ing|ment)?|weather|politic\w*|election|president|"
    r"movie|song|lyrics|poem|essay|homework|translate|travel|flight|hotel|"
    r"capital of|math problem|tax|lawyer|legal advice)\b|"
    r"코딩|프로그래밍|파이썬|레시피|요리|주식|코인|날씨|정치|선거|영화|노래|숙제|번역|여행|맛집",
    re.I,
)


_SWIM_RE = re.compile(
    r"swim|stroke|freestyle|backstroke|breaststroke|butterfly|medley|drill|pool|lap|catch|kick|"
    r"pull|turn|breath|taper|css|rpe|pace|training|workout|set\b|session|technique|dive|start|"
    r"수영|자유형|배영|평영|접영|영법|드릴|훈련|킥|풀|호흡|턴|대회|테이퍼|페이스",
    re.I,
)


_PLAN_EDIT_RE = re.compile(
    r"(세트표|훈련\s*계획|플랜).{0,15}(수정|바꿔|변경|삭제|덮어)|"
    r"(modify|change|edit|rewrite|delete|overwrite)\s+(my\s+|the\s+)?(plan|sets?\b|set table|training plan)",
    re.I | re.S,
)


PAIN_RE = re.compile(
    r"\b(pain|painful|hurts?|hurting|sore|soreness|injur\w*|strain(?:ed)?|sprain(?:ed)?|"
    r"tendin\w+|torn|tear|swollen|swelling|ache|aching|impingement)\b|"
    r"통증|아[프픈파팠픔]|부상|다쳤|다친|염증|파열|삐|근육통|쑤시|저려|저림",
    re.IGNORECASE)


_SET_CHANGED_RE = re.compile(r"(세트표|계획).{0,12}(수정했|변경했|바꿨|업데이트했)|"
                             r"(updated|modified|changed)\s+(your|the)\s+(plan|set)", re.I)


def mentions_pain(text: str) -> bool:
    return bool(PAIN_RE.search(text or ""))


def _trace(stage: str, rule, decision: str, detail: str = "") -> None:
    tracing.record_guardrail(stage, rule, decision, detail)


def check_input(text: str) -> InputVerdict:
    """Run before the agent loop. A refusal means the model and tools must not be called."""
    v = _check_input(text or "")
    notes = (["pain_flag: G-02 safety rules added"] if v.pain else []) +         (["plan_edit_flag: G-03 read-only suggestions"] if v.plan_edit else [])
    _trace("input", v.rule or ("G-03" if v.plan_edit else None),
           "allow" if v.allowed else "refuse", "; ".join(notes))
    return v


def _check_input(text: str) -> InputVerdict:
    if _SECRET_REQUEST_RE.search(text):
        return InputVerdict(False, SECRET_REFUSAL, "G-05")
    if _OFF_TOPIC_RE.search(text) and not _SWIM_RE.search(text):
        return InputVerdict(False, OFF_TOPIC_REFUSAL, "G-05")
    err = plan_input_error(text)
    if err:
        return InputVerdict(False, err, "G-04")
    return InputVerdict(True, pain=mentions_pain(text), plan_edit=bool(_PLAN_EDIT_RE.search(text)))


def safety_system(system: str, verdict: InputVerdict) -> str:
    if verdict.pain:
        system += MEDICAL_RULES
    if verdict.plan_edit:
        system += PLAN_EDIT_RULES
    return system


def check_output(reply: str, verdict: InputVerdict | None = None) -> str:
    """Run after the agent loop: redact secrets, guarantee the Korean safety notices."""
    raw = (reply or "").strip()
    reply = redact(raw)
    if reply != raw:
        _trace("output", "G-05", "redact", "credential value removed from reply")
    if verdict is not None and verdict.pain and MEDICAL_NOTICE not in reply:
        reply = f"{reply}\n\n{MEDICAL_NOTICE}"
        _trace("output", "G-02", "append_notice", "medical notice added")
    edit_asked = verdict is not None and verdict.plan_edit
    if (edit_asked or _SET_CHANGED_RE.search(reply)) and SET_EDIT_NOTICE not in reply:
        reply = f"{reply}\n\n{SET_EDIT_NOTICE}"
        _trace("output", "G-03", "append_notice", "set-edit notice added")
    return reply
