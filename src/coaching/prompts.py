"""Prompt template of the text-only coach (plan/logs are read-only context)."""


SYSTEM = ("You are an expert swim coach for an advanced masters swimmer. Answer questions about "
          "strokes, technique, body position and drills in plain text, recommending specific "
          "drills when relevant. You cannot analyse photos or video. Do not rewrite the training "
          "plan; use it only as context. Reply in the user's language.")


def build_prompt(question: str, plan: dict | None, logs: list[dict], css: list[dict],
                 history: list[dict]) -> str:
    p = ""
    if plan:
        p += (f"[Context, read-only] Event {plan['event']}, competition {plan['competition_date']}, "
              f"{plan['sessions_per_week']} sessions/week x {plan['session_minutes']} min. "
              "Phases: " + ", ".join(f"w{w['week_number']}:{w['phase']}" for w in plan["weeks"]) + "\n")
        for s in plan["sessions"][-plan["sessions_per_week"]:]:
            p += f"- {s['title']}: " + "; ".join(
                f"{x['type']} {x.get('description', '')} RPE{x['intensity_rpe']}" for x in s["sets"]) + "\n"
    if logs:
        p += "[Recent logs]\n" + "\n".join(
            f"- {l['log_date']}: {l['distance_m']} m RPE {l['perceived_rpe']} {l['notes']}"
            for l in logs[-5:]) + "\n"
    if css:
        p += f"[Latest CSS pace] {css[-1]['css_pace_s_per_100m']} s/100m\n"
    if history:
        p += "[Conversation so far]\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in history[-10:]) + "\n"
    return p + f"\nQuestion: {question}"
