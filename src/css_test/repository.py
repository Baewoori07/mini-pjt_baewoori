"""Persistence for CSS test results."""


def add_css(conn, test_date: str, t400: float, t200: float, pace: float) -> int:
    cur = conn.execute(
        "INSERT INTO css_results (test_date,t400_s,t200_s,css_pace_s_per_100m) VALUES (?,?,?,?)",
        (test_date, t400, t200, pace))
    conn.commit()
    return cur.lastrowid


def list_css(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM css_results ORDER BY test_date,id")]
