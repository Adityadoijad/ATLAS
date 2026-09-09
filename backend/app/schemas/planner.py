from datetime import date

from pydantic import BaseModel, Field


class ActivitySchema(BaseModel):
    time: str = Field(min_length=1, max_length=32)
    description: str = Field(min_length=1, max_length=500)
    location: str = Field(min_length=1, max_length=200)
    estimated_cost: float = Field(ge=0)


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


class PlannerRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    budget: float = Field(gt=0)
    travelers: int = Field(default=1, ge=1)
    preferences: dict[str, object] = Field(default_factory=dict)
    currency: str = Field(default="INR", min_length=3, max_length=3)
