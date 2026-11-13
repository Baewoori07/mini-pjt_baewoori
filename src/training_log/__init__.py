"""Training-log domain: what the swimmer actually did (feeds next-week generation)."""
from .repository import add_log, list_logs
from .schemas import LogRequest

__all__ = ["LogRequest", "add_log", "list_logs"]
