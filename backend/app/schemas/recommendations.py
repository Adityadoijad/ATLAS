from pydantic import BaseModel, Field, field_validator

from app.core.validators import coerce_numeric_cost


class RecommendationSchema(BaseModel):
    destination_id: str = Field(min_length=1)
    score: float = Field(ge=0)
    reason: str = Field(min_length=1)


class DiscoveredDestinationSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=400)
    categories: list[str] = Field(min_length=1, max_length=4)
    estimated_budget_inr: float = Field(ge=0)
    best_season: str = Field(min_length=1, max_length=50)
    duration_days: int = Field(ge=1, le=30)

    @field_validator("estimated_budget_inr", mode="before")
    @classmethod
    def _normalize_budget(cls, value: object) -> object:
        return coerce_numeric_cost(value)
