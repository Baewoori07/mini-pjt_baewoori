"""Text-coach request model."""
from pydantic import BaseModel, Field


class CoachRequest(BaseModel):
    message: str = Field(min_length=1)
    plan_id: int | None = None
