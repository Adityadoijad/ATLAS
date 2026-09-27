"""
Pydantic schemas for the /api/chat endpoint.
"""
from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.core.validators import coerce_numeric_cost


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User message to the ATLAS assistant.")


class ChatPlanSchema(BaseModel):
    """Structured summary of a complete trip plan the assistant just produced.

    This exists so the UI can tell "the assistant finished a real plan" from
    "the assistant answered a question", without the frontend guessing from the
    prose. Present only when the assistant actually generated a full day-by-day
    plan; absent for questions, clarifications and ordinary conversation.

    It is a summary for handing to the booking flow — not a persisted trip.
    """

    title: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date
    travelers: int = Field(ge=1, le=50)
    # The assistant's own estimate for the whole trip. Reuses the planner's
    # currency-string normalizer so "₹30,000" and "30000 INR" don't slip
    # through as text the booking flow would render as NaN.
    estimated_cost: float = Field(ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)

    @field_validator("estimated_cost", mode="before")
    @classmethod
    def _normalize_estimated_cost(cls, value: object) -> object:
        return coerce_numeric_cost(value)


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI-generated response from ATLAS assistant.")
    plan: ChatPlanSchema | None = Field(
        default=None,
        description="Set only when the reply is a complete trip plan the user can take to booking.",
    )
