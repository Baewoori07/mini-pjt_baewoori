"""Periodized plan + weekly set tables; regenerates at most twice when a session is too long (G-01)."""
import json
import math
import re
from datetime import date, timedelta

from .. import guardrails
from ..shared import tracing
from ..shared.llm import LLMClient
from . import repository
from .prompts import SYSTEM, build_next_week_prompt, build_prompt
from .schemas import PHASES, SET_TYPES, PlanError, PlanNotFound


MAX_REGENERATIONS = 2


def need_plan(conn, plan_id: int) -> dict:
    """Stored plan or PlanNotFound (-> 404)."""
    plan = repository.get_plan(conn, plan_id)
    if not plan:
        raise PlanNotFound("plan not found")
    return plan


def count_weeks(start: date, competition: date) -> int:
    return max(1, math.ceil((competition - start).days / 7))


def _extract_json(text: str) -> dict:
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    else:
        a, b = text.find("{"), text.rfind("}")
        if a != -1 and b > a:
            text = text[a:b + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise PlanError(f"invalid JSON from model: {e}") from e
    if not isinstance(data, dict):
        raise PlanError("model output is not a JSON object")
    return data


def parse_and_check(data: dict, inputs: dict, n_weeks: int) -> tuple[list[dict], list[dict]]:
    weeks = data.get("weeks")
    if not isinstance(weeks, list) or len(weeks) != n_weeks:
        raise PlanError(f"expected {n_weeks} weeks")
    order = []
    for w in weeks:
        if not isinstance(w, dict) or w.get("phase") not in PHASES:
            raise PlanError("bad phase")
        order.append(PHASES.index(w["phase"]))
    if order != sorted(order):
        raise PlanError("phases not in base->build->taper order")
    return weeks, check_sessions(data.get("sessions"), inputs)


def check_sessions(sessions, inputs: dict) -> list[dict]:
    if not isinstance(sessions, list) or len(sessions) != inputs["sessions_per_week"]:
        raise PlanError(f"expected {inputs['sessions_per_week']} sessions")
    out = []
    for s in sessions:
        sets = s.get("sets") if isinstance(s, dict) else None
        if not sets or not isinstance(sets, list):
            raise PlanError("session without sets")
        for st in sets:
            rpe = st.get("intensity_rpe")
            if not isinstance(rpe, (int, float)) or not 1 <= rpe <= 10:
                raise PlanError("intensity_rpe must be 1-10")
            if not isinstance(st.get("est_minutes"), (int, float)) or st["est_minutes"] < 0:
                raise PlanError("est_minutes missing")
            if st.get("type") not in SET_TYPES:
                raise PlanError("bad set type")
        total = round(sum(st["est_minutes"] for st in sets), 2)
        out.append({"title": s.get("title", "Session"), "sets": sets, "total_minutes": total})
    return out


def _trace_duration(sessions: list[dict], limit: float, attempt: int, bad: list[str]) -> None:
    """Record the app-side duration check (SERVICE.md tool validate_duration) in the trace."""
    tracing.record_tool_call(
        "validate_duration", {"session_minutes": limit, "attempt": attempt},
        {"sessions": [{"title": s["title"], "total_minutes": s["total_minutes"]} for s in sessions],
         "over_duration": bad, "ok": not bad})


def generate_next_week(llm: LLMClient, plan: dict, week: dict, logs: list[dict],
                       css: list[dict]) -> dict:
    limit = plan["session_minutes"]
    overrun, attempts = None, 0
    while True:
        raw = llm.complete(SYSTEM, build_next_week_prompt(plan, week, logs, css, overrun))
        sessions = check_sessions(_extract_json(raw).get("sessions"), plan)
        for s in sessions:
            s["over_duration"] = guardrails.duration_overrun(s["total_minutes"], limit)
        bad = [f"{s['title']} = {s['total_minutes']} min > {limit}" for s in sessions
               if s["over_duration"]]
        _trace_duration(sessions, limit, attempts, bad)
        if not bad or attempts >= MAX_REGENERATIONS:
            break
        attempts += 1
        overrun = bad
    return {"sessions": sessions, "regeneration_attempts": attempts}


def generate_plan(llm: LLMClient, inputs: dict, today: date | None = None) -> dict:
    """Generate full-period plan + this week's sessions; regenerate <=2 times if over duration."""
    today = today or date.today()
    comp = date.fromisoformat(inputs["competition_date"])
    n_weeks = count_weeks(today, comp)
    limit = inputs["session_minutes"]
    overrun: list[str] | None = None
    attempts = 0
    while True:
        raw = llm.complete(SYSTEM, build_prompt(inputs, n_weeks, overrun))
        weeks, sessions = parse_and_check(_extract_json(raw), inputs, n_weeks)
        for s in sessions:
            s["over_duration"] = guardrails.duration_overrun(s["total_minutes"], limit)
        bad = [f"{s['title']} = {s['total_minutes']} min > {limit}" for s in sessions
               if s["over_duration"]]
        _trace_duration(sessions, limit, attempts, bad)
        if not bad or attempts >= MAX_REGENERATIONS:
            break
        attempts += 1
        overrun = bad
    weeks_out = [{"week_number": i, "phase": w["phase"],
                  "start_date": (today + timedelta(weeks=i - 1)).isoformat()}
                 for i, w in enumerate(weeks, 1)]
    return {"start_date": today.isoformat(), "weeks": weeks_out, "sessions": sessions,
            "regeneration_attempts": attempts}
