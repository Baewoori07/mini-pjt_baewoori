"""SQLite connection and the full table schema (all domains share one local DB file).

Domain-specific queries live in each domain's ``repository.py``.
"""
import os
import sqlite3


DEFAULT_DB_PATH = os.environ.get("SWIM_DB_PATH", "data/swim.db")


SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  competition_date TEXT NOT NULL,
  event TEXT NOT NULL,
  sessions_per_week INTEGER NOT NULL,
  session_minutes INTEGER NOT NULL,
  start_date TEXT NOT NULL,
  regeneration_attempts INTEGER NOT NULL DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS weeks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id INTEGER NOT NULL REFERENCES plans(id),
  week_number INTEGER NOT NULL,
  phase TEXT NOT NULL CHECK (phase IN ('base','build','taper')),
  start_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id INTEGER NOT NULL REFERENCES plans(id),
  week_number INTEGER NOT NULL,
  session_index INTEGER NOT NULL,
  title TEXT NOT NULL,
  sets_json TEXT NOT NULL,
  total_minutes REAL NOT NULL,
  over_duration INTEGER NOT NULL DEFAULT 0
);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    path = path or DEFAULT_DB_PATH
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.executescript(SCHEMA2)
    return conn


SCHEMA2 = """
CREATE TABLE IF NOT EXISTS training_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id INTEGER NOT NULL REFERENCES plans(id),
  log_date TEXT NOT NULL,
  week_number INTEGER,
  session_index INTEGER,
  completed_sets TEXT NOT NULL DEFAULT '',
  distance_m INTEGER NOT NULL DEFAULT 0,
  perceived_rpe REAL NOT NULL,
  notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS css_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  test_date TEXT NOT NULL,
  t400_s REAL NOT NULL,
  t200_s REAL NOT NULL,
  css_pace_s_per_100m REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS coaching_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  plan_id INTEGER,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def init_extra(conn):
    conn.executescript(SCHEMA2)
