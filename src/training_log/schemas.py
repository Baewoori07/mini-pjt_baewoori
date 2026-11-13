"""Training-log request model."""
from datetime import date

from pydantic import BaseModel, Field


class LogRequest(BaseModel):
    log_date: date
    week_number: int | None = Field(default=None, ge=1)
    session_index: int | None = Field(default=None, ge=1)
    completed_sets: str = ""
    distance_m: int = Field(default=0, ge=0)
    perceived_rpe: float = Field(ge=1, le=10)
    notes: str = ""
