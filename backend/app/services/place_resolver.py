"""Check that the planner's place names are real, before the trip is stored.

The prompt asks for real places; this verifies it. A name the geocoder cannot
find yields no travel distance and no travel time, so catching it at
generation time is worth a few seconds — and it warms the cache, so the route
endpoint answers instantly afterwards.

Two things this deliberately does NOT do:

*No coordinates are written into the plan.* Locations stay names. The route
service geocodes them as it always has, which keeps one place responsible for
turning names into points.

*No unresolvable name is replaced by a guess.* Not the destination centre, not
a nearby stop, not a fabricated coordinate. It stays exactly as the planner
wrote it and the itinerary reports its travel time as unavailable, which is
the honest answer.

Repair is deterministic and conservative: no second call to the model, and no
edit that could turn one real place into a different real place.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.schemas.planner import GeneratedTripPlanSchema
from app.services.integrations.maps import GeocodingUnavailable, geocode_place

logger = logging.getLogger(__name__)

# Nominatim runs at one request per second, and trip generation already makes
# the user wait on the model. This caps how long verification can add; names
# beyond it are simply left for the route endpoint to resolve later.
MAX_LOOKUPS = 20

# Qualifiers written for a reader that mean nothing to a geocoder.
_VAGUE_FRAGMENT = re.compile(
    r"\b(near|close to|opposite|beside|next to|around|within|en route|on the way|nearby)\b",
    re.IGNORECASE,
)

# Words that can never, alone, be the name of a place. Kept deliberately short.
# An earlier, longer list included "palace", "temple", "lake" and "station" —
# which wrongly classified "City Palace" and "Lake Pichola" as unusable and so
# refused to look up places that plainly exist. Whether a name is real is
# Nominatim's judgement, not a word list's; this only stops a *trim* from
# collapsing a name into a bare noun.
_BARE_TYPE_WORDS = frozenset({
    "restaurant", "cafe", "café", "eatery", "diner", "bar", "hotel", "stay",
    "lodge", "resort", "guesthouse", "hostel", "market", "bazaar", "centre",
    "center", "complex", "viewpoint", "point", "spot", "place", "venue",
    "terrace", "rooftop", "area", "the", "a", "an", "local", "traditional",
})


# Trailing descriptors safe to drop as a last resort. Removing one moves the
# query from a feature to the landmark containing it — "Lake Pichola jetty"
# becomes "Lake Pichola" — which is a different subject in words but the same
# spot on a map. That makes the result an approximation, so it is recorded as
# one rather than passed off as an exact match.
_TRAILING_DESCRIPTORS = (
    "jetty", "ghat", "cafe", "café", "restaurant", "market", "bazaar",
    "viewpoint", "view point", "gate", "entrance", "complex", "grounds",
)


@dataclass
class PlaceResolution:
    """What happened to one distinct location name."""

    original: str
    query: str
    resolved: bool
    # Set when a repair produced the name that worked, so the plan can be
    # rewritten to the name ATLAS can actually find.
    repaired_to: str | None = None
    # True when the repair reached a containing landmark rather than the exact
    # feature named. Recorded so the provenance is never overstated.
    approximate: bool = False


@dataclass
class ResolutionReport:
    """Internal diagnostics. Not a user-facing quality score."""

    total: int = 0
    resolved: int = 0
    unresolved_names: list[str] = field(default_factory=list)
    repaired: dict[str, str] = field(default_factory=dict)
    approximate_names: list[str] = field(default_factory=list)
    # True when the geocoder itself was unreachable, which is a different
    # situation from the planner having written unusable names.
    geocoder_unavailable: bool = False

    @property
    def resolution_rate(self) -> float | None:
        """resolved / total, or None when there was nothing to check."""
        if self.total == 0:
            return None
        return round(self.resolved / self.total, 3)

    def as_dict(self) -> dict[str, object]:
        return {
            "total_locations": self.total,
            "resolved_locations": self.resolved,
            "place_resolution_rate": self.resolution_rate,
            "unresolved_locations": self.unresolved_names,
            "repaired_locations": self.repaired,
            "approximate_locations": self.approximate_names,
            "geocoder_unavailable": self.geocoder_unavailable,
        }


def _too_thin_to_trim_to(name: str) -> bool:
    """Whether a trimmed name has collapsed into something meaningless.

    Only guards repairs, never what the planner wrote. Real places are
    routinely built from ordinary words — "City Palace", "Lake Pichola",
    "Jagdish Temple" — so judging a name unreal from its wording would skip
    places that plainly exist. This stops a trim producing a bare "Restaurant",
    nothing more.
    """
    words = [word for word in re.split(r"[^\w']+", name) if word]
    if not words:
        return True
    return all(word.casefold() in _BARE_TYPE_WORDS for word in words)


def _qualify(name: str, destination: str, boarding_name: str = "") -> str:
    """Add the destination city so a bare landmark name is findable.

    The boarding location is the exception: it is where the traveller departs
    from, which is somewhere else entirely. Qualifying it produces "Nagpur
    Railway Station, Udaipur" — a place that does not exist — so it is looked
    up as written.
    """
    if boarding_name and _names_same_place(name, boarding_name):
        return name
    city = destination.strip()
    if not city or city.casefold() in name.casefold():
        return name
    return f"{name}, {city}"


def _names_same_place(left: str, right: str) -> bool:
    a, b = left.strip().casefold(), right.strip().casefold()
    return bool(a and b and (a == b or a in b or b in a))


def repair_candidates(location: str) -> list[tuple[str, bool]]:
    """Progressively simpler forms of a location, best first.

    Each entry is (name, approximate). Every candidate is a prefix of the
    original subject — words are only ever removed from the end, never
    substituted — so a repair can narrow what is being named but can never
    swap in a different place.

    A name that is purely descriptive still gets tried once — deciding it is
    unreal from its wording is not something this can do reliably, and guessing
    wrong would skip a real place. Nominatim decides; the prompt is what stops
    such names being written in the first place.
    """
    original = location.strip()
    if not original:
        return []

    # What the planner wrote is always tried first. Classifying a name as
    # unreal from its wording alone is not something this can do reliably, and
    # guessing wrong would skip a real place; Nominatim decides.
    candidates: list[tuple[str, bool]] = [(original, False)]

    # Drop a parenthetical aside: "City Palace (entry tickets)".
    without_parens = re.sub(r"\s*\([^)]*\)", "", original).strip()
    if without_parens and without_parens != original and not _too_thin_to_trim_to(without_parens):
        candidates.append((without_parens, False))

    # Keep only the part before the first comma — the place itself, without
    # the reader-facing context the planner appended.
    head = candidates[-1][0].split(",")[0].strip()
    if head and head != candidates[-1][0] and not _too_thin_to_trim_to(head):
        candidates.append((head, False))

    # Drop a trailing vague qualifier that survived without a comma:
    # "Ambrai Restaurant near hotel".
    current = candidates[-1][0]
    match = _VAGUE_FRAGMENT.search(current)
    if match and match.start() > 0:
        trimmed = current[: match.start()].strip().rstrip(",-–—").strip()
        if trimmed and not _too_thin_to_trim_to(trimmed):
            candidates.append((trimmed, False))

    # Last resort: step back from a feature to the landmark containing it.
    # This one is an approximation and is flagged as such.
    current = candidates[-1][0]
    words = current.split()
    if len(words) >= 3 and words[-1].casefold().strip(".,") in _TRAILING_DESCRIPTORS:
        # At least three words in, so at least two survive. Trimming "Mitra
        # Restaurant" down to "Mitra" would hand the geocoder a single common
        # word that could match anything at all — a different place wearing the
        # right name, which is exactly what repair must never produce.
        trimmed = " ".join(words[:-1]).strip()
        if trimmed and not _too_thin_to_trim_to(trimmed):
            candidates.append((trimmed, True))

    # Preserve order, drop repeats.
    seen: set[str] = set()
    unique: list[tuple[str, bool]] = []
    for name, approximate in candidates:
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append((name, approximate))
    return unique


def plan_locations(plan: GeneratedTripPlanSchema) -> list[str]:
    """Every location the plan names, in order, with repeats."""
    return [activity.location for day in plan.days for activity in day.activities]


async def _resolve_one(
    location: str, destination: str, boarding_name: str = ""
) -> PlaceResolution:
    """Try a location, then progressively simpler forms of it."""
    candidates = repair_candidates(location)
    if not candidates:
        return PlaceResolution(original=location, query=location, resolved=False)

    for index, (name, approximate) in enumerate(candidates):
        query = _qualify(name, destination, boarding_name)
        place = await geocode_place(query)
        if place is None:
            continue
        return PlaceResolution(
            original=location,
            query=query,
            resolved=True,
            # Only report a repair when the name actually changed.
            repaired_to=None if index == 0 else name,
            approximate=approximate,
        )

    return PlaceResolution(original=location, query=candidates[0][0], resolved=False)


async def verify_plan_locations(
    plan: GeneratedTripPlanSchema, destination: str, boarding_name: str = ""
) -> ResolutionReport:
    """Check every distinct location, repairing names where it is safe to.

    Mutates `plan` in place: a location that only resolved after repair is
    rewritten to the repaired name, so the traveller sees the name ATLAS can
    find and the route service geocodes it straight from cache.

    Never raises. A geocoder outage leaves the plan untouched and is recorded
    in the report, because "we could not check" is not "the names are wrong".
    """
    report = ResolutionReport()

    # Distinct names only: an itinerary returns to the same hotel four times,
    # and that is one lookup, not four. Order is kept so the cap falls on the
    # end of the trip rather than at random.
    distinct: list[str] = []
    seen: set[str] = set()
    for location in plan_locations(plan):
        key = location.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            distinct.append(location)

    resolutions: dict[str, PlaceResolution] = {}
    lookups = 0
    for location in distinct:
        if lookups >= MAX_LOOKUPS:
            # Left unverified rather than declared bad. The route endpoint
            # still resolves it later; it just does not count here.
            break
        try:
            resolution = await _resolve_one(location, destination, boarding_name)
        except GeocodingUnavailable:
            report.geocoder_unavailable = True
            logger.info("Geocoder unavailable; leaving planner locations unverified.")
            break
        lookups += 1
        resolutions[location.strip().casefold()] = resolution

        report.total += 1
        if resolution.resolved:
            report.resolved += 1
            if resolution.repaired_to:
                report.repaired[location] = resolution.repaired_to
            if resolution.approximate:
                report.approximate_names.append(location)
        else:
            report.unresolved_names.append(location)

    # Rewrite the plan to the names that worked.
    for day in plan.days:
        for activity in day.activities:
            resolution = resolutions.get(activity.location.strip().casefold())
            if resolution is not None and resolution.repaired_to:
                activity.location = resolution.repaired_to

    if report.total:
        logger.info(
            "Planner locations: %d/%d resolved for %r (%d repaired).",
            report.resolved, report.total, destination, len(report.repaired),
        )
    return report
