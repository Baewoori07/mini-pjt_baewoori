"""Persistence for training logs."""


def add_log(conn, plan_id: int, d: dict) -> int:
    cur = conn.execute(
        "INSERT INTO training_logs (plan_id,log_date,week_number,session_index,completed_sets,"
        "distance_m,perceived_rpe,notes) VALUES (?,?,?,?,?,?,?,?)",
        (plan_id, d["log_date"], d.get("week_number"), d.get("session_index"),
         d.get("completed_sets", ""), d.get("distance_m", 0), d["perceived_rpe"],
         d.get("notes", "")))
    conn.commit()
    return cur.lastrowid


def list_logs(conn, plan_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT * FROM training_logs WHERE plan_id=? ORDER BY log_date,id", (plan_id,))]
