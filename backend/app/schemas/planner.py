from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.core.validators import coerce_numeric_cost


class ActivitySchema(BaseModel):
    time: str = Field(min_length=1, max_length=32)
    description: str = Field(min_length=1, max_length=500)
    location: str = Field(min_length=1, max_length=200)
    estimated_cost: float = Field(ge=0)

    @field_validator("estimated_cost", mode="before")
    @classmethod
    def _normalize_estimated_cost(cls, value: object) -> object:
        return coerce_numeric_cost(value)


class DayPlanSchema(BaseModel):
    day_number: int = Field(ge=1)
    date: date
    title: str = Field(min_length=1, max_length=200)
    activities: list[ActivitySchema] = Field(min_length=1)


class GeneratedTripPlanSchema(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    total_budget: float = Field(ge=0)
    days: list[DayPlanSchema] = Field(min_length=1)
    is_realtime_data: bool = True
    fallback_reason: str | None = None

    @field_validator("total_budget", mode="before")
    @classmethod
    def _normalize_total_budget(cls, value: object) -> object:
        return coerce_numeric_cost(value)


class PlannerRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    budget: float = Field(gt=0)
    travelers: int = Field(default=1, ge=1)
    preferences: dict[str, object] = Field(default_factory=dict)
    currency: str = Field(default="INR", min_length=3, max_length=3)
