"""Personalized destination recommendations, scored from a user's real trip
preferences and saved places (no LLM call — fast, deterministic, and safe to
call on every dashboard load).

CATALOG mirrors the destination ids/categories in
frontend/src/data/destinations.ts (name/image/description/etc. live there;
this only needs id + tags to score against). Keep the ids in sync if that
catalog changes.
"""
import random
from itertools import groupby
from typing import Iterable

from app.models.saved_place import SavedPlace
from app.models.trip import Trip
from app.models.user import User
from app.schemas.recommendations import RecommendationSchema

CATALOG: list[dict[str, object]] = [
    {"id": "kerala", "name": "Kerala", "rating": 4.8, "categories": ["nature", "beaches", "food"]},
    {"id": "kolkata", "name": "Kolkata", "rating": 4.7, "categories": ["culture", "cities", "food"]},
    {"id": "mussoorie", "name": "Mussoorie", "rating": 4.6, "categories": ["mountains", "nature", "cities"]},
    {"id": "goa", "name": "Goa", "rating": 4.6, "categories": ["beaches", "food", "culture"]},
    {"id": "mumbai", "name": "Mumbai", "rating": 4.9, "categories": ["cities", "culture", "food"]},
    {"id": "manali", "name": "Manali", "rating": 4.7, "categories": ["mountains", "adventure", "nature"]},
    {"id": "jaipur", "name": "Jaipur", "rating": 4.7, "categories": ["culture", "cities", "adventure"]},
    {"id": "kyoto", "name": "Kyoto", "rating": 4.9, "categories": ["culture", "nature", "food"]},
    {"id": "bali", "name": "Bali", "rating": 4.7, "categories": ["beaches", "nature", "adventure"]},
    {"id": "santorini", "name": "Santorini", "rating": 4.8, "categories": ["beaches", "culture", "nature"]},
    {"id": "dubai", "name": "Dubai", "rating": 4.6, "categories": ["cities", "adventure", "culture"]},
    {"id": "swiss-alps", "name": "Swiss Alps", "rating": 4.9, "categories": ["mountains", "nature", "adventure"]},
]

_DEFAULT_REASON = "Popular with ATLAS travellers"
_CATALOG_BY_ID = {str(item["id"]): item for item in CATALOG}


def _flatten_preference_tags(preferences: object) -> Iterable[str]:
    if not isinstance(preferences, dict):
        return
    for value in preferences.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    yield item.strip().lower()
        elif isinstance(value, str) and value.strip():
            yield value.strip().lower()


def _build_tag_profile(trips: list[Trip], saved_places: list[SavedPlace]) -> dict[str, int]:
    tag_counts: dict[str, int] = {}
    for trip in trips:
        for tag in _flatten_preference_tags(trip.preferences):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    for place in saved_places:
        for raw in (place.category, place.type):
            if raw and raw.strip():
                tag = raw.strip().lower()
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        # A saved place whose place_id matches a known destination (e.g. the
        # heart button on a destination card saves place_id="goa" with a
        # generic category="Destinations") also carries that destination's
        # own tags — otherwise saving a destination directly contributes no
        # signal at all, which defeats the point of "recommended for you".
        catalog_match = _CATALOG_BY_ID.get(place.place_id.strip().lower())
        if catalog_match:
            for tag in catalog_match["categories"]:  # type: ignore[union-attr]
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return tag_counts


def _shuffle_within_ties(ranked: list[tuple], key) -> list[tuple]:
    """Groups already sorted by `key` descending; randomize order *within*
    each tied group so refreshing surfaces different, equally-relevant picks
    instead of the exact same order every time (real ties get shuffled, the
    ranking signal itself never does)."""
    out: list[tuple] = []
    for _, group in groupby(ranked, key=key):
        bucket = list(group)
        random.shuffle(bucket)
        out.extend(bucket)
    return out


def build_recommendations(user: User, *, limit: int = 6) -> list[RecommendationSchema]:
    tag_profile = _build_tag_profile(list(user.trips), list(user.saved_places))

    if not tag_profile:
        ranked = sorted(CATALOG, key=lambda item: item["rating"], reverse=True)
        ranked = _shuffle_within_ties(ranked, key=lambda item: item["rating"])
        return [
            RecommendationSchema(destination_id=str(item["id"]), score=0.0, reason=_DEFAULT_REASON)
            for item in ranked[:limit]
        ]

    scored: list[tuple[dict[str, object], float, list[str]]] = []
    for item in CATALOG:
        categories = [str(c).lower() for c in item["categories"]]  # type: ignore[union-attr]
        matched = [tag for tag in categories if tag_profile.get(tag)]
        score = float(sum(tag_profile.get(tag, 0) for tag in categories))
        scored.append((item, score, matched))

    scored.sort(key=lambda entry: entry[1], reverse=True)
    scored = _shuffle_within_ties(scored, key=lambda entry: entry[1])

    results: list[RecommendationSchema] = []
    for item, score, matched in scored[:limit]:
        if matched:
            top_tags = ", ".join(tag.title() for tag in matched[:2])
            reason = f"Matches your interest in {top_tags}"
        else:
            reason = _DEFAULT_REASON
        results.append(RecommendationSchema(destination_id=str(item["id"]), score=score, reason=reason))
    return results
