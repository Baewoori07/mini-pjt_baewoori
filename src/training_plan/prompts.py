"""Prompt templates for full-plan and next-week generation."""


SYSTEM = ("You are an expert swim coach creating periodized training plans for an advanced "
          "masters swimmer. Express intensity as RPE (1-10). Output valid JSON only.")


def build_prompt(inputs: dict, n_weeks: int, overrun: list[str] | None = None) -> str:
    p = (
        f"Competition date: {inputs['competition_date']}\nEvent: {inputs['event']}\n"
        f"Sessions per week: {inputs['sessions_per_week']}\n"
        f"Session duration (minutes): {inputs['session_minutes']}\n"
        f"Total weeks until competition: {n_weeks}\n\n"
        'Return ONLY JSON: {"weeks":[{"week_number":1,"phase":"base|build|taper"}, ...],'
        '"sessions":[{"title":str,"sets":[{"type":"warm-up|main|drill|cool-down",'
        '"description":str,"distance_m":int,"reps":int,"intensity_rpe":1-10,'
        '"est_minutes":number}]}]}\n'
        f"'weeks' must have exactly {n_weeks} entries ordered base -> build -> taper. "
        f"'sessions' are for week 1 only: exactly {inputs['sessions_per_week']} sessions. "
        "Each set's est_minutes includes rest; the sum of est_minutes per session "
        "(warm-up and rest included) must not exceed the session duration."
    )
    if overrun:
        p += "\n\nPrevious attempt exceeded the duration: " + "; ".join(overrun) + ". Shorten the sets."
    return p


def build_next_week_prompt(plan: dict, week: dict, logs: list[dict], css: list[dict],
                           overrun: list[str] | None = None) -> str:
    phases = ", ".join(f"{w['week_number']}:{w['phase']}" for w in plan["weeks"])
    p = (
        f"Competition date: {plan['competition_date']}\nEvent: {plan['event']}\n"
        f"Sessions per week: {plan['sessions_per_week']}\n"
        f"Session duration (minutes): {plan['session_minutes']}\n"
        f"Generate week {week['week_number']} of {len(plan['weeks'])} (phase: {week['phase']}).\n"
        f"Full plan phases: {phases}\n\n"
    )
    if logs:
        lines = [
            f"- {l['log_date']}: {l['distance_m']} m, perceived RPE {l['perceived_rpe']}, "
            f"completed: {l['completed_sets']}, notes: {l['notes']}" for l in logs[-10:]]
        p += "Recent training logs:\n" + "\n".join(lines) + "\n"
    if css:
        c = css[-1]
        p += (f"Latest CSS test ({c['test_date']}): 400m {c['t400_s']}s, 200m {c['t200_s']}s, "
              f"CSS pace {c['css_pace_s_per_100m']}s/100m.\n")
    if logs or css:
        p += ("Since logs/CSS results exist, prefer pace / cycle-time notation (e.g. 'CSS+2s', "
              "'1:20 per 100') in the optional 'intensity_pace' field, keeping intensity_rpe too. "
              "Adjust volume and intensity from the logs.\n")
    p += (
        'Return ONLY JSON: {"sessions":[{"title":str,"sets":[{"type":"warm-up|main|drill|cool-down",'
        '"description":str,"distance_m":int,"reps":int,"intensity_rpe":1-10,"intensity_pace":str?,'
        '"est_minutes":number}]}]}\n'
        f"Exactly {plan['sessions_per_week']} sessions. Each set's est_minutes includes rest; the "
        "per-session sum (warm-up and rest included) must not exceed the session duration."
    )
    if overrun:
        p += "\n\nPrevious attempt exceeded the duration: " + "; ".join(overrun) + ". Shorten the sets."
    return p
