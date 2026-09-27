"""Dynamic "Discover India" recommendation service.

Orchestrates:
  1. Groq → candidate destinations (name/state/description/reason/tags only)
  2. Nominatim → validate each candidate is a real place in India + get coords
  3. Wikimedia → fetch a real photo + attribution for each validated destination
  4. In-process cache so Groq is not called on every homepage render

Architecture principles that must not be violated:
  - Groq NEVER provides coordinates — those come from Nominatim.
  - Groq NEVER provides image URLs — those come from Wikimedia.
  - The fallback dataset is used ONLY when Groq fails. It is NOT the primary
    recommendation source and must NOT be used unless Groq is unavailable.
  - A Nominatim failure for a single candidate silently discards that candidate.
  - A Wikimedia failure for a single destination keeps the destination but sets
    image.url = null. It never aborts the overall response.
"""
import asyncio
import logging
import random
from datetime import datetime
from time import monotonic
from typing import Any

from pydantic import ValidationError

from app.schemas.recommendations import (
    DiscoverIndiaDestinationSchema,
    GroqIndiaCandidateSchema,
    ImageAttributionSchema,
)
from app.services.ai_service import (
    AIConfigurationError,
    AIQuotaExceededError,
    extract_json,
    generate,
)
from app.services.integrations.maps import validate_india_destination
from app.services.integrations.photos import get_destination_photo_with_metadata

logger = logging.getLogger(__name__)

# ── Cache ─────────────────────────────────────────────────────────────────────
# TTL is randomised within [6 h, 10 h] so that multiple running processes don't
# all expire at the same second and hammer Groq simultaneously.
_CACHE_TTL_MIN = 6 * 3600
_CACHE_TTL_MAX = 10 * 3600
_cache: dict[str, tuple[float, list[DiscoverIndiaDestinationSchema]]] = {}
_CACHE_KEY = "india_recommendations"


def _cache_ttl() -> float:
    return random.uniform(_CACHE_TTL_MIN, _CACHE_TTL_MAX)


def _get_cached() -> list[DiscoverIndiaDestinationSchema] | None:
    entry = _cache.get(_CACHE_KEY)
    if entry and monotonic() - entry[0] < entry[1]:  # type: ignore[arg-type]
        return entry[2]  # type: ignore[return-value]
    return None


def _set_cache(results: list[DiscoverIndiaDestinationSchema]) -> None:
    _cache[_CACHE_KEY] = (monotonic(), _cache_ttl(), results)  # type: ignore[assignment]


# ── Season detection ──────────────────────────────────────────────────────────

def _current_season() -> str:
    """Return a human-readable season string based on the current month."""
    month = datetime.now().month
    if month in (12, 1, 2):
        return "winter (Dec-Feb) — ideal for south India, Rajasthan, beaches"
    elif month in (3, 4, 5):
        return "spring/summer (Mar-May) — ideal for hills, Himalayan foothills, Northeast India"
    elif month in (6, 7, 8):
        return "monsoon (Jun-Aug) — ideal for Kerala, Goa off-season, Ladakh, Spiti"
    else:
        return "post-monsoon/autumn (Sep-Nov) — ideal for wildlife, Rajasthan, Himalayas, Northeast India"


# ── Groq prompt ───────────────────────────────────────────────────────────────

_SYSTEM_INSTRUCTION = """You are an expert Indian travel curator. You suggest
authentic, diverse, real Indian destinations. You prioritise lesser-known and
emerging destinations alongside iconic ones. You never invent places — every
suggestion must be a real, verifiable location in India. You never provide
coordinates or image URLs — those are obtained from authoritative databases."""

_PROMPT_TEMPLATE = """Suggest exactly 10 real Indian travel destinations for a
traveller visiting India. Current season: {season}.

Return a JSON object with a single key "destinations" whose value is an array
of exactly 10 items. Each item MUST have exactly these fields:
- name (string): the destination name, e.g. "Majuli"
- state (string): the Indian state or union territory, e.g. "Assam"
- country (string): always "India"
- description (string, 1-2 sentences, 40-160 chars): what makes this place special
- reason (string, 1 sentence, 30-120 chars): why it suits the current season
- tags (array of 1-4 strings from: culture, nature, mountains, beaches, heritage,
  wildlife, adventure, spiritual, food, slow-travel, festival)
- search_query (string): a specific search phrase for finding photos of this
  destination, e.g. "Majuli river island Assam" or "Chopta Bugyal meadow Uttarakhand"

STRICT RULES:
- Do NOT include latitude, longitude, image URLs or any coordinates.
- Do NOT return the same destination twice.
- Spread across ALL regions: at least 1 from North, 1 from South, 1 from East,
  1 from West, 2 from Northeast, 1 from Central India.
- Spread across travel styles: include mountains, beaches OR backwaters,
  heritage, wildlife, culture, adventure, spiritual, food/slow-travel.
- Include at least 3 destinations that are NOT mainstream tourist hotspots.
- The current season is {season} — suggest places that are good to visit NOW.
- Verify every place is a real, existing location in India.
"""


# ── Fallback dataset ──────────────────────────────────────────────────────────
# Used ONLY when Groq fails. Never as the primary source. Images are fetched
# fresh (not hardcoded). If Wikimedia also fails, image.url stays null.

_FALLBACK_CANDIDATES: list[dict[str, Any]] = [
    {
        "name": "Majuli",
        "state": "Assam",
        "description": "The world's largest river island, home to vibrant Vaishnava monasteries and the Mising tribal culture.",
        "reason": "A serene retreat that is accessible year-round and especially beautiful in winter.",
        "tags": ["culture", "nature", "slow-travel"],
        "search_query": "Majuli river island Assam",
    },
    {
        "name": "Ziro",
        "state": "Arunachal Pradesh",
        "description": "Pine-fringed valley of the Apatani tribe, known for rice fields and an intimate music festival.",
        "reason": "Cool highland climate and lush green landscapes make this ideal for autumn visits.",
        "tags": ["culture", "nature", "mountains"],
        "search_query": "Ziro valley Arunachal Pradesh Apatani",
    },
    {
        "name": "Hampi",
        "state": "Karnataka",
        "description": "Ruined capital of the Vijayanagara Empire set among surreal boulder-strewn landscapes.",
        "reason": "Winter months make exploring the vast open-air ruins comfortable and rewarding.",
        "tags": ["heritage", "culture", "adventure"],
        "search_query": "Hampi ruins Vijayanagara Karnataka",
    },
    {
        "name": "Dhanushkodi",
        "state": "Tamil Nadu",
        "description": "A ghost town at India's tip where the Bay of Bengal meets the Indian Ocean.",
        "reason": "Quiet and otherworldly, best visited in the cooler winter months.",
        "tags": ["beaches", "heritage", "slow-travel"],
        "search_query": "Dhanushkodi beach Tamil Nadu Pamban",
    },
    {
        "name": "Chopta",
        "state": "Uttarakhand",
        "description": "A pristine highland meadow known as the 'Mini Switzerland of India', gateway to Tungnath temple.",
        "reason": "Post-monsoon season reveals snow-capped peaks and clear trekking trails.",
        "tags": ["mountains", "nature", "spiritual"],
        "search_query": "Chopta Tungnath Chandrashila Uttarakhand trek",
    },
    {
        "name": "Mawlynnong",
        "state": "Meghalaya",
        "description": "Asia's cleanest village, surrounded by living root bridges and emerald valleys.",
        "reason": "Post-monsoon greenery makes the valley and root bridges spectacularly lush.",
        "tags": ["nature", "culture", "slow-travel"],
        "search_query": "Mawlynnong village Meghalaya living root bridge",
    },
    {
        "name": "Gokarna",
        "state": "Karnataka",
        "description": "A laid-back coastal temple town with pristine beaches south of Goa.",
        "reason": "Winter is perfect for beach walks and the calm surf at Om Beach.",
        "tags": ["beaches", "spiritual", "slow-travel"],
        "search_query": "Gokarna beach Karnataka Om beach",
    },
    {
        "name": "Spiti",
        "state": "Himachal Pradesh",
        "description": "A cold-desert mountain valley with ancient monasteries perched on dramatic cliffs.",
        "reason": "Early autumn is the last accessible window before roads close for winter.",
        "tags": ["mountains", "adventure", "heritage"],
        "search_query": "Spiti Valley Key monastery Himachal Pradesh",
    },
]


# ── Validation & enrichment ───────────────────────────────────────────────────

async def _validate_candidate(
    candidate: GroqIndiaCandidateSchema,
) -> DiscoverIndiaDestinationSchema | None:
    """Validate one Groq candidate through Nominatim and attach Wikimedia image.

    Returns None if Nominatim cannot confirm the destination is in India.
    A Wikimedia failure is tolerated — the destination is returned with
    image.url = null.
    """
    geo = await validate_india_destination(candidate.name, candidate.state)
    if geo is None:
        logger.info(
            "Discarding candidate %r %r — Nominatim could not confirm India location.",
            candidate.name, candidate.state,
        )
        return None

    try:
        photo = await get_destination_photo_with_metadata(
            candidate.search_query or candidate.name, candidate.state
        )
    except Exception as exc:
        logger.warning(
            "Failed to retrieve photo for candidate %r (%r): %s",
            candidate.name, candidate.state, exc
        )
        photo = None

    return DiscoverIndiaDestinationSchema(
        name=candidate.name,
        state=candidate.state,
        country="India",
        full_name=f"{candidate.name}, {candidate.state}, India",
        description=candidate.description,
        reason=candidate.reason,
        tags=candidate.tags,
        latitude=float(geo["latitude"]),
        longitude=float(geo["longitude"]),
        image=ImageAttributionSchema(
            url=photo.get("url") if photo else None,
            source=photo.get("source") if photo else None,
            source_url=photo.get("source_url") if photo else None,
            author=photo.get("author") if photo else None,
            license=photo.get("license") if photo else None,
        ),
    )


def _enforce_diversity(
    destinations: list[DiscoverIndiaDestinationSchema],
    target: int = 6,
) -> list[DiscoverIndiaDestinationSchema]:
    """Return up to `target` destinations, capping any single state at 2.

    This prevents e.g. 4 destinations from Himachal Pradesh ending up in the
    same carousel. States within the same broad region are not further capped
    at the region level — that's handled upstream in the Groq prompt.
    """
    state_counts: dict[str, int] = {}
    result: list[DiscoverIndiaDestinationSchema] = []
    for dest in destinations:
        count = state_counts.get(dest.state, 0)
        if count < 2:
            result.append(dest)
            state_counts[dest.state] = count + 1
        if len(result) >= target:
            break
    return result


async def _build_from_candidates(
    candidates: list[GroqIndiaCandidateSchema],
) -> list[DiscoverIndiaDestinationSchema]:
    """Run Nominatim + Wikimedia enrichment for all candidates concurrently."""
    tasks = [_validate_candidate(c) for c in candidates]
    results_raw = await asyncio.gather(*tasks)
    validated = [r for r in results_raw if r is not None]
    # Deduplicate by name (case-insensitive)
    seen: set[str] = set()
    deduped: list[DiscoverIndiaDestinationSchema] = []
    for dest in validated:
        key = dest.name.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(dest)
    return _enforce_diversity(deduped)


# ── Fallback enrichment ───────────────────────────────────────────────────────

async def _build_fallback() -> list[DiscoverIndiaDestinationSchema]:
    """Build recommendations from the controlled fallback dataset.

    Images are still fetched from Wikimedia (not hardcoded).
    Nominatim validation is skipped for the fallback — these are pre-verified
    known places. Hardcoded lat/lon are used so the fallback never queries
    Nominatim, which may itself be failing.
    """
    # Pre-validated coordinates for the fallback set.
    _FALLBACK_COORDS: dict[str, tuple[float, float]] = {
        "Majuli": (26.9525, 94.1667),
        "Ziro": (27.5482, 93.8314),
        "Hampi": (15.3350, 76.4600),
        "Dhanushkodi": (9.1622, 79.4209),
        "Chopta": (30.4839, 79.2088),
        "Mawlynnong": (25.2015, 91.9165),
        "Gokarna": (14.5479, 74.3188),
        "Spiti": (32.2432, 78.0342),
    }

    async def _enrich(c: dict[str, Any]) -> DiscoverIndiaDestinationSchema:
        lat, lon = _FALLBACK_COORDS.get(c["name"], (20.5937, 78.9629))
        photo = await get_destination_photo_with_metadata(
            c.get("search_query") or c["name"], c.get("state", "India")
        )
        return DiscoverIndiaDestinationSchema(
            name=c["name"],
            state=c.get("state", "India"),
            country="India",
            full_name=f"{c['name']}, {c.get('state', 'India')}, India",
            description=c["description"],
            reason=c["reason"],
            tags=c.get("tags", ["nature"]),
            latitude=lat,
            longitude=lon,
            image=ImageAttributionSchema(
                url=photo.get("url") if photo else None,
                source=photo.get("source") if photo else None,
                source_url=photo.get("source_url") if photo else None,
                author=photo.get("author") if photo else None,
                license=photo.get("license") if photo else None,
            ),
            is_fallback=True,
        )

    results = await asyncio.gather(*[_enrich(c) for c in _FALLBACK_CANDIDATES[:6]])
    return list(results)


# ── Groq call ─────────────────────────────────────────────────────────────────

async def _call_groq() -> list[GroqIndiaCandidateSchema]:
    """Call Groq and parse+validate the candidates.

    Raises DiscoverIndiaGroqError on any failure — callers fall back to the
    controlled dataset rather than propagating the error to the frontend.
    """
    season = _current_season()
    prompt = _PROMPT_TEMPLATE.format(season=season)
    try:
        raw = await generate(
            prompt,
            system_instruction=_SYSTEM_INSTRUCTION,
            json_mode=True,
            max_tokens=3000,
            temperature=0.85,  # Higher temperature → more variety across requests
        )
    except (AIConfigurationError, AIQuotaExceededError) as exc:
        raise _GroqError(str(exc)) from exc
    except Exception as exc:
        raise _GroqError(f"Groq call failed: {exc}") from exc

    try:
        data = extract_json(raw)
        if isinstance(data, dict):
            # Unwrap {"destinations": [...]} wrapper
            data = next((v for v in data.values() if isinstance(v, list)), None)
        if not isinstance(data, list):
            raise ValueError("Expected a list of destination candidates.")
        candidates: list[GroqIndiaCandidateSchema] = []
        for item in data:
            try:
                candidates.append(GroqIndiaCandidateSchema.model_validate(item))
            except ValidationError as ve:
                logger.warning("Skipping invalid Groq candidate: %s — %s", item, ve)
        if not candidates:
            raise ValueError("No valid candidates after schema validation.")
        return candidates
    except (ValueError, TypeError) as exc:
        logger.warning("Groq India response invalid: %s. Raw: %s", exc, raw[:500])
        raise _GroqError(f"Groq returned an invalid response: {exc}") from exc


class _GroqError(RuntimeError):
    pass


# ── Public API ────────────────────────────────────────────────────────────────

async def get_india_recommendations() -> list[DiscoverIndiaDestinationSchema]:
    """Return AI-curated India recommendations, using cache when fresh.

    Flow:
      cache hit  → return cached
      cache miss → Groq → Nominatim → Wikimedia → cache → return
      Groq fail  → fallback dataset → Wikimedia → return (not cached)

    Never raises into the caller. A completely empty list is returned only if
    even the fallback fails (extremely unlikely).
    """
    cached = _get_cached()
    if cached is not None:
        logger.debug("Returning %d cached India recommendations.", len(cached))
        return cached

    # Primary path: Groq → validate → enrich
    try:
        candidates = await _call_groq()
        results = await _build_from_candidates(candidates)
        if results:
            _set_cache(results)
            logger.info(
                "Built %d Groq-generated India recommendations (from %d candidates).",
                len(results), len(candidates),
            )
            return results
        logger.warning("Groq produced candidates but none passed Nominatim validation — using fallback.")
    except _GroqError as exc:
        logger.warning("Groq India recommendations failed: %s — using fallback.", exc)

    # Fallback path: controlled dataset with fresh Wikimedia images
    try:
        fallback = await _build_fallback()
        logger.info("Returning %d fallback India recommendations.", len(fallback))
        return fallback
    except Exception as exc:
        logger.error("Fallback India recommendations also failed: %s", exc)
        return []


def invalidate_cache() -> None:
    """Clear the in-process cache (useful for testing)."""
    _cache.clear()
