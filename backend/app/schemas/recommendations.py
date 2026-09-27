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
    # A real photograph of the place, resolved from Wikimedia after the model
    # replies. Optional on purpose: None means "no genuine photo found", and
    # the UI shows a placeholder rather than an unrelated stock image.
    image_url: str | None = None

    @field_validator("estimated_budget_inr", mode="before")
    @classmethod
    def _normalize_budget(cls, value: object) -> object:
        return coerce_numeric_cost(value)


# ── Discover India schemas ────────────────────────────────────────────────────


class GroqIndiaCandidateSchema(BaseModel):
    """What Groq is allowed to return for each India recommendation candidate.

    Strictly forbids lat/lon and image URLs — those always come from
    authoritative external services (Nominatim and Wikimedia respectively).
    """

    name: str = Field(min_length=1, max_length=120)
    state: str = Field(min_length=1, max_length=80)
    country: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    reason: str = Field(min_length=1, max_length=300)
    tags: list[str] = Field(min_length=1, max_length=6)
    # Used as the Wikimedia search query; Groq may refine the phrasing here.
    search_query: str = Field(min_length=1, max_length=150)


class ImageAttributionSchema(BaseModel):
    """Image metadata returned alongside every Discover India card.

    All fields are nullable — a missing image or incomplete metadata must never
    cause the recommendation response to fail.
    """

    url: str | None = None
    source: str | None = None        # e.g. "Wikimedia Commons"
    source_url: str | None = None    # URL to the Wikimedia file page
    author: str | None = None
    license: str | None = None


class DiscoverIndiaDestinationSchema(BaseModel):
    """Fully-enriched India recommendation returned to the frontend.

    Coordinates come from Nominatim (never from Groq). The image object comes
    from Wikimedia (never from Groq). Groq contributes only recommendation
    content: name, state, description, reason, tags.
    """

    name: str
    state: str
    country: str = "India"
    full_name: str          # e.g. "Majuli, Assam, India"
    description: str
    reason: str
    tags: list[str]
    latitude: float
    longitude: float
    image: ImageAttributionSchema
    is_fallback: bool = False

