"""Persistence for chat history (redacted before storage by the callers)."""


def add_message(conn, plan_id, role: str, content: str):
    conn.execute("INSERT INTO coaching_messages (plan_id,role,content) VALUES (?,?,?)",
                 (plan_id, role, content))
    conn.commit()


def list_messages(conn, plan_id=None) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT role,content,created_at FROM coaching_messages WHERE plan_id IS ? ORDER BY id",
        (plan_id,))]
