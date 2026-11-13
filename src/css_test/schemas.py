"""CSS test request model."""
from datetime import date

from pydantic import BaseModel, Field


class CssRequest(BaseModel):
    test_date: date
    t400_s: float = Field(gt=0)
    t200_s: float = Field(gt=0)
