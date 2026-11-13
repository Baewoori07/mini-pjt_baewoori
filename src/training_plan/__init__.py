"""Training-plan domain: periodization (base -> build -> taper) and weekly set tables."""
from .repository import add_week_sessions, get_plan, latest_plan_id, save_plan
from .schemas import PHASES, SET_TYPES, PlanError, PlanNotFound, PlanRequest
from .service import (MAX_REGENERATIONS, check_sessions, count_weeks, generate_next_week, generate_plan,
                      need_plan)

__all__ = ["MAX_REGENERATIONS", "PHASES", "PlanError", "PlanRequest", "SET_TYPES", "add_week_sessions",
           "check_sessions", "count_weeks", "generate_next_week", "generate_plan", "get_plan",
           "latest_plan_id", "need_plan", "PlanNotFound", "save_plan"]
