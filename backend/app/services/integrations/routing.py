"""Real road distance and travel time between itinerary stops, via OSRM.

Free and keyless, on the same OpenStreetMap data the rest of ATLAS already
uses — so this adds no provider the project did not already depend on.

Why `/route` and not `/table`: a trip is a *sequence*, and `/route` with N
coordinates returns N-1 `legs`, each carrying the distance and duration of one
consecutive pair, in a single request. A table would compute the full N x N
matrix and throw away everything off the diagonal.

The one rule this module exists to enforce: **a missing leg is null, never
zero.** Zero is a real answer meaning "these two stops are the same place",
and using it for "we could not find out" turns an outage into a confident
lie on the itinerary. Every failure path here yields None plus a reason.

Data (c) OpenStreetMap contributors, ODbL. Routing by the public OSRM demo
server, which carries no availability guarantee — hence the circuit breaker
and the honest unavailable state.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import monotonic

import httpx

from app.services.integrations.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

routing_breaker = CircuitBreaker()

OSRM_ENDPOINT = "https://router.project-osrm.org"
_USER_AGENT = "ATLAS-Travel-Planner/1.0 (https://github.com/Adityadoijad/ATLAS; student project)"

# The demo server is shared infrastructure. A trip longer than this is
# truncated rather than sent as one enormous request; the itinerary still
# renders, the legs past the cap simply report as unavailable.
MAX_STOPS = 25

# Roads do not move. Caching by the exact coordinate sequence means reopening
# an itinerary, or two users planning the same saved trip, costs nothing.
_CACHE_TTL_SECONDS = 24 * 60 * 60
_cache: dict[tuple, tuple[float, list["RouteLeg"]]] = {}
_inflight: dict[tuple, asyncio.Task] = {}

_HTTP_TIMEOUT_SECONDS = 12.0


class RoutingUnavailable(RuntimeError):
    """Routing could not be computed. Callers report it; they never fill in zero."""


@dataclass(frozen=True)
class RouteLeg:
    """One consecutive pair of stops.

    `distance_km` and `duration_minutes` are None together, and only when the
    router could not answer for this leg. `routing_available` is the flag the
    UI branches on so it never has to infer meaning from a number.
    """

    from_index: int
    to_index: int
    distance_km: float | None
    duration_minutes: float | None

    @property
    def routing_available(self) -> bool:
        return self.distance_km is not None and self.duration_minutes is not None

    def as_dict(self) -> dict[str, object]:
        return {
            "from_index": self.from_index,
            "to_index": self.to_index,
            "distance_km": self.distance_km,
            "duration_minutes": self.duration_minutes,
            "routing_available": self.routing_available,
        }


def _unavailable_legs(count: int) -> list[RouteLeg]:
    """Explicitly-unknown legs. Never zero-valued ones."""
    return [RouteLeg(index, index + 1, None, None) for index in range(count)]


def _cache_key(coordinates: list[tuple[float, float]]) -> tuple:
    # Rounded to ~10 m: enough that geocoder jitter for the same stop reuses
    # the entry, far too fine to collapse two genuinely different places.
    return tuple((round(lat, 4), round(lon, 4)) for lat, lon in coordinates)


def _format_coordinates(coordinates: list[tuple[float, float]]) -> str:
    """OSRM takes lon,lat — the reverse of every other ATLAS integration."""
    return ";".join(f"{lon},{lat}" for lat, lon in coordinates)


async def _request_legs(coordinates: list[tuple[float, float]]) -> list[RouteLeg]:
    path = f"{OSRM_ENDPOINT}/route/v1/driving/{_format_coordinates(coordinates)}"

    async with httpx.AsyncClient(
        timeout=_HTTP_TIMEOUT_SECONDS, headers={"User-Agent": _USER_AGENT}
    ) as client:
        try:
            # `overview=false` drops the route geometry: ATLAS draws no polyline,
            # and the geometry is by far the largest part of the response.
            response = await client.get(path, params={"overview": "false"})
        except httpx.HTTPError as exc:
            raise RoutingUnavailable(
                f"The routing service could not be reached ({type(exc).__name__})."
            ) from None

    if response.status_code >= 400:
        raise RoutingUnavailable(f"The routing service returned HTTP {response.status_code}.")

    try:
        payload = response.json()
    except ValueError:
        raise RoutingUnavailable("The routing service returned an unreadable response.") from None

    code = payload.get("code")
    if code == "NoRoute":
        # A genuine answer: there is no drivable road between these points
        # (an island, or a stop geocoded into the sea). Still not zero.
        raise RoutingUnavailable("No drivable route connects these stops.")
    if code != "Ok":
        raise RoutingUnavailable(f"The routing service could not plan this route ({code}).")

    routes = payload.get("routes")
    if not isinstance(routes, list) or not routes:
        raise RoutingUnavailable("The routing service returned no route.")

    raw_legs = routes[0].get("legs")
    if not isinstance(raw_legs, list):
        raise RoutingUnavailable("The routing service returned no legs.")

    expected = len(coordinates) - 1
    if len(raw_legs) != expected:
        # Rather than guess which leg is which, report the whole hop set as
        # unknown — a misaligned distance is worse than an absent one.
        raise RoutingUnavailable("The routing service returned an unexpected number of legs.")

    legs: list[RouteLeg] = []
    for index, leg in enumerate(raw_legs):
        distance = leg.get("distance") if isinstance(leg, dict) else None
        duration = leg.get("duration") if isinstance(leg, dict) else None
        if not isinstance(distance, (int, float)) or not isinstance(duration, (int, float)):
            # One unusable leg does not discard the rest; this one is unknown.
            legs.append(RouteLeg(index, index + 1, None, None))
            continue
        legs.append(RouteLeg(
            from_index=index,
            to_index=index + 1,
            distance_km=round(float(distance) / 1000, 1),
            duration_minutes=round(float(duration) / 60),
        ))
    return legs


async def get_route_legs(coordinates: list[tuple[float, float]]) -> list[RouteLeg]:
    """Distance and duration for each consecutive pair of stops.

    Returns exactly `len(coordinates) - 1` legs, in order. Raises
    RoutingUnavailable when the router could not answer at all — callers
    surface that state rather than substituting zeros.
    """
    if len(coordinates) < 2:
        return []
    if len(coordinates) > MAX_STOPS:
        logger.info("Routing %d stops, truncated to the first %d.", len(coordinates), MAX_STOPS)
        coordinates = coordinates[:MAX_STOPS]

    key = _cache_key(coordinates)

    entry = _cache.get(key)
    if entry and monotonic() - entry[0] < _CACHE_TTL_SECONDS:
        return entry[1]

    existing = _inflight.get(key)
    if existing is not None:
        # Two viewers opening the same itinerary at once share one request.
        # `shield` keeps a cancelled waiter from killing it for the other.
        return await asyncio.shield(existing)

    async def run() -> list[RouteLeg]:
        try:
            legs = await routing_breaker.call(lambda: _request_legs(coordinates))
            # Only a real answer is cached. A failure raises, so an outage can
            # never be replayed for a day as though it were routing data.
            _cache[key] = (monotonic(), legs)
            return legs
        finally:
            _inflight.pop(key, None)

    task = asyncio.ensure_future(run())
    _inflight[key] = task
    try:
        return await asyncio.shield(task)
    except RuntimeError as exc:
        # An open breaker raises a bare RuntimeError; callers should only ever
        # have to handle one failure type.
        if isinstance(exc, RoutingUnavailable):
            raise
        if "circuit is open" in str(exc):
            raise RoutingUnavailable(
                "Routing is paused after repeated failures from the routing service."
            ) from None
        raise
