"""Plan request model, phase/set enums and errors."""
from datetime import date

from pydantic import BaseModel, Field, field_validator

from .. import guardrails


PHASES = ("base", "build", "taper")


SET_TYPES = ("warm-up", "main", "drill", "cool-down")


class PlanError(Exception):
    pass


class PlanNotFound(LookupError):
    """Raised when a plan id does not exist (mapped to HTTP 404 in main.py)."""


class PlanRequest(BaseModel):
    competition_date: date
    event: str = Field(min_length=1)
    sessions_per_week: int = Field(ge=1, le=14)
    session_minutes: int = Field(ge=15, le=300)

    @field_validator("competition_date")
    @classmethod
    def future(cls, v):
        return guardrails.validate_competition_date(v)

    @field_validator("event")
    @classmethod
    def supported_event(cls, v):
        return guardrails.validate_event(v)
