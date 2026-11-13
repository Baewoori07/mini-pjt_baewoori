"""Persistence for plans, weeks and sessions."""
import json


def save_plan(conn, *, inputs: dict, start_date: str, weeks: list[dict],
              sessions: list[dict], regeneration_attempts: int) -> int:
    cur = conn.execute(
        "INSERT INTO plans (competition_date,event,sessions_per_week,session_minutes,"
        "start_date,regeneration_attempts) VALUES (?,?,?,?,?,?)",
        (inputs["competition_date"], inputs["event"], inputs["sessions_per_week"],
         inputs["session_minutes"], start_date, regeneration_attempts))
    pid = cur.lastrowid
    for w in weeks:
        conn.execute("INSERT INTO weeks (plan_id,week_number,phase,start_date) VALUES (?,?,?,?)",
                     (pid, w["week_number"], w["phase"], w["start_date"]))
    for i, s in enumerate(sessions, 1):
        conn.execute(
            "INSERT INTO sessions (plan_id,week_number,session_index,title,sets_json,"
            "total_minutes,over_duration) VALUES (?,?,?,?,?,?,?)",
            (pid, 1, i, s["title"], json.dumps(s["sets"]), s["total_minutes"],
             int(s["over_duration"])))
    conn.commit()
    return pid


def get_plan(conn, plan_id: int) -> dict | None:
    p = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
    if not p:
        return None
    weeks = [dict(r) for r in conn.execute(
        "SELECT week_number,phase,start_date FROM weeks WHERE plan_id=? ORDER BY week_number",
        (plan_id,))]
    sessions = []
    for r in conn.execute("SELECT * FROM sessions WHERE plan_id=? ORDER BY week_number,session_index",
                          (plan_id,)):
        sessions.append({
            "week_number": r["week_number"], "session_index": r["session_index"],
            "title": r["title"], "sets": json.loads(r["sets_json"]),
            "total_minutes": r["total_minutes"], "over_duration": bool(r["over_duration"]),
        })
    return {
        "id": p["id"], "competition_date": p["competition_date"], "event": p["event"],
        "sessions_per_week": p["sessions_per_week"], "session_minutes": p["session_minutes"],
        "start_date": p["start_date"], "regeneration_attempts": p["regeneration_attempts"],
        "weeks": weeks, "sessions": sessions,
    }


def add_week_sessions(conn, plan_id: int, week_number: int, sessions: list[dict]):
    for i, s in enumerate(sessions, 1):
        conn.execute(
            "INSERT INTO sessions (plan_id,week_number,session_index,title,sets_json,"
            "total_minutes,over_duration) VALUES (?,?,?,?,?,?,?)",
            (plan_id, week_number, i, s["title"], json.dumps(s["sets"]), s["total_minutes"],
             int(s["over_duration"])))
    conn.commit()



def latest_plan_id(conn) -> int | None:
    return conn.execute("SELECT MAX(id) FROM plans").fetchone()[0]
