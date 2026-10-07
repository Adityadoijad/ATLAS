from datetime import date, timedelta
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.validators import coerce_numeric_cost

# The cost buckets the itinerary UI reports against. Kept as a strict literal
# so an unexpected value (e.g. "hotel", "sightseeing") fails validation and
# goes through the existing retry/fallback path rather than being silently
# guessed at or bucketed wrongly in the frontend.
ActivityCategory = Literal["accommodation", "travel", "food", "activity"]


class ActivitySchema(BaseModel):
    time: str = Field(min_length=1, max_length=32)
    description: str = Field(min_length=1, max_length=500)
    location: str = Field(min_length=1, max_length=200)
    estimated_cost: float = Field(ge=0)
    category: ActivityCategory

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
    """A complete itinerary.

    `start_date` and `end_date` are INCLUSIVE, so a plan must carry one day per
    calendar date in the range: Oct 1 -> Oct 8 is eight days, not seven.
    """

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

    @model_validator(mode="after")
    def _days_must_cover_the_whole_range(self) -> "GeneratedTripPlanSchema":
        """Every calendar date in the range gets exactly one day, in order.

        The model was previously free to return any number of days as long as
        each fell inside the range, and `min_length=1` accepted the result. An
        eight-day trip came back with four days and was persisted without
        complaint, because nothing downstream ever counted them.

        A plan that fails here raises ValidationError, which the generator
        already treats as "output ATLAS cannot trust": it retries once, then
        falls back to a plan clearly marked `is_realtime_data=False`. A short
        itinerary is never silently saved, and days are never duplicated or
        padded to make the count work — the plan is rejected instead.
        """
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")

        expected_dates = [
            self.start_date + timedelta(days=offset)
            for offset in range((self.end_date - self.start_date).days + 1)
        ]

        if len(self.days) != len(expected_dates):
            raise ValueError(
                f"itinerary must contain {len(expected_dates)} days for "
                f"{self.start_date.isoformat()} to {self.end_date.isoformat()} inclusive, "
                f"but {len(self.days)} were generated"
            )

        # Checked positionally, which catches duplicate numbers, duplicate
        # dates, gaps and out-of-range dates in one pass.
        for index, (day, expected) in enumerate(zip(self.days, expected_dates), start=1):
            if day.day_number != index:
                raise ValueError(
                    f"day numbers must run 1..{len(expected_dates)} in order; "
                    f"position {index} has day_number {day.day_number}"
                )
            if day.date != expected:
                raise ValueError(
                    f"day {index} must be dated {expected.isoformat()}, got {day.date.isoformat()}"
                )

        return self


class BoardingLocation(BaseModel):
    """Where the journey actually begins.

    Coordinates are resolved server-side from `name` — the user types
    "Nagpur Railway Station", never a latitude. They are optional on the way in
    and always present on the way out, because a boarding location that could
    not be placed is rejected rather than stored half-resolved.

    `display_name` is the geocoder's own label for what it matched, kept so the
    itinerary can show which "Nagpur Railway Station" it routed from.
    """

    name: str = Field(min_length=1, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    display_name: str | None = Field(default=None, max_length=500)


class PlannerRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=200)
    # Optional on the schema so trips created by other callers (and every trip
    # that predates this field) still validate. The planning endpoint requires
    # it for new trips; see routes/planner.py.
    boarding_location: BoardingLocation | None = None
    start_date: date
    end_date: date
    budget: float = Field(gt=0)
    travelers: int = Field(default=1, ge=1)
    preferences: dict[str, object] = Field(default_factory=dict)
    currency: str = Field(default="INR", min_length=3, max_length=3)
