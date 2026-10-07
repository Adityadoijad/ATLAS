"""The one ordered list of places a trip visits.

Both the itinerary timeline and the map route render from this. Building it in
two places is how they drift apart — a map that starts at the hotel while the
itinerary starts at the station is worse than either being wrong alone,
because nothing on screen says which to believe.

The sequence is: boarding location (when the trip has one), then every
itinerary stop in order. Legs are computed between consecutive entries, so
stop 0 -> stop 1 is the journey from where the traveller actually departs.

Nothing here fabricates a coordinate or a distance. A stop the geocoder cannot
place stays unresolved, and the legs touching it report as unavailable.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.models.trip import Trip
from app.services.integrations.maps import geocode_places
from app.services.integrations.routing import RouteLeg, RoutingUnavailable, get_route_legs

logger = logging.getLogger(__name__)

# Geocoding runs at one request per second, per Nominatim's policy, so the
# sequence is capped to keep a first-time lookup within a reasonable wait.
# Results are cached for a day afterwards, so reopening a trip is instant, and
# most names are already cached because generation verified them.
#
# 12 was too low: a three-day itinerary runs to roughly fifteen stops, so the
# last afternoon fell off the end of the route and every row after the cap
# reported its travel time as unavailable. Sized above a typical trip, and
# still under OSRM's own limit.
MAX_SEQUENCE_STOPS = 20

# The planner sometimes packs a whole journey into one location string.
_LEG_SEPARATORS = ("→", "->", "—>")


@dataclass
class Stop:
    index: int
    label: str
    query: str
    latitude: float | None
    longitude: float | None
    is_boarding: bool

    @property
    def resolved(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def as_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "label": self.label,
            "query": self.query,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "is_boarding": self.is_boarding,
            "resolved": self.resolved,
        }


def _split_legs(location: str) -> list[str]:
    parts = [location]
    for separator in _LEG_SEPARATORS:
        parts = [piece for part in parts for piece in part.split(separator)]
    return [part.strip() for part in parts if part.strip()]


def _same_place(left: str, right: str) -> bool:
    """Whether two stop labels name the same place.

    Substring containment rather than equality, because the planner writes the
    boarding point as "Nagpur Railway Station" in one row and the itinerary
    writes "Nagpur Railway Station, Platform 4" in another. Compared only
    against the immediately preceding stop, so a genuine return visit later in
    the trip still counts as a journey.
    """
    a = left.strip().casefold()
    b = right.strip().casefold()
    if not a or not b:
        return False
    return a == b or a in b or b in a


# Qualifiers the planner adds for the reader's benefit that mean nothing to a
# geocoder. "Mitra Restaurant, near hotel" is not a place; "Mitra Restaurant"
# might be.
_VAGUE_FRAGMENTS = (
    "near ", "close to", "opposite", "beside", "next to", "around ",
    "within ", "en route", "on the way", "nearby",
)


def _place_name(stop: str) -> str:
    """The searchable part of a planner-written location.

    The planner writes locations for a human: "Hotel Lake Palace, Lake Pichola"
    or "Mitra Restaurant, near hotel". Geocoding the whole string fails, while
    the leading place name usually resolves. Everything after the first comma
    is dropped, and a vague fragment anywhere is treated as noise.
    """
    head = stop.split(",")[0].strip()
    if not head:
        return stop.strip()
    lowered = head.casefold()
    if any(fragment in lowered for fragment in _VAGUE_FRAGMENTS):
        return stop.strip()
    return head


def _qualify(stop: str, destination: str) -> str:
    """'Hadimba Temple' is ambiguous worldwide; ', Manali' makes it findable."""
    name = _place_name(stop)
    city = destination.strip()
    if not city or city.casefold() in name.casefold():
        return name
    return f"{name}, {city}"


def itinerary_locations(trip: Trip) -> list[str]:
    """Stop names from the trip's itinerary days, in order.

    Activities are stored pipe-delimited as
    `time | description | location | cost | category`; the location is field 3.
    Rows written before the category existed have four fields and still parse.
    """
    locations: list[str] = []
    for day in sorted(trip.itinerary_days, key=lambda d: d.day_number):
        for line in (day.description or "").split("\n"):
            fields = [field.strip() for field in line.split("|")]
            if len(fields) < 3 or not fields[2]:
                continue
            locations.extend(_split_legs(fields[2]))
    return locations


def build_sequence(trip: Trip) -> list[Stop]:
    """The canonical ordered stops, before geocoding.

    Consecutive repeats collapse: a hotel that is both the night's stay and the
    next morning's breakfast is one place to travel to, not a zero-distance leg
    against itself. A non-consecutive return to the hotel is kept, because
    that is a real journey.
    """
    entries: list[tuple[str, str, bool]] = []

    boarding = trip.boarding_location or {}
    boarding_name = str(boarding.get("name") or "")
    if boarding_name:
        entries.append((boarding_name, boarding_name, True))

    for location in itinerary_locations(trip):
        label = location
        # A stop naming the boarding location is that same place, so it is not
        # qualified with the destination city. "Nagpur Railway Station, Udaipur"
        # is a place that does not exist, and asking for it produces an
        # unresolvable stop and two dead legs either side of it.
        query = location if _same_place(location, boarding_name) else _qualify(location, trip.destination or "")
        if entries and _same_place(entries[-1][0], label):
            # The planner routinely opens day one at the boarding point
            # ("Board train from Nagpur Railway Station"). That is the stop we
            # already have, not a second visit to it.
            continue
        entries.append((label, query, False))

    return [
        Stop(index=index, label=label, query=query, latitude=None, longitude=None, is_boarding=is_boarding)
        for index, (label, query, is_boarding) in enumerate(entries[:MAX_SEQUENCE_STOPS])
    ]


async def resolve_sequence(trip: Trip) -> tuple[list[Stop], list[RouteLeg], str | None]:
    """Geocode the stops and route between them.

    Returns (stops, legs, unavailable_reason). There is always one leg per
    consecutive pair, so the caller can index them against the stops; a leg
    that could not be computed carries nulls and `routing_available: false`,
    never a zero.
    """
    stops = build_sequence(trip)
    if len(stops) < 2:
        # A single stop has no journey between anything. Not an error.
        return stops, [], None

    boarding = trip.boarding_location or {}
    resolved = await geocode_places([stop.query for stop in stops])
    for stop, place in zip(stops, resolved):
        if stop.is_boarding and boarding.get("latitude") is not None:
            # The boarding location was geocoded and stored when the trip was
            # planned. Reuse those coordinates rather than re-resolving: they
            # are what the user confirmed, and a geocoder that has since
            # changed its mind must not silently move the trip's origin.
            stop.latitude = float(boarding["latitude"])
            stop.longitude = float(boarding["longitude"])
            continue
        if place is None:
            continue
        stop.latitude = float(place["latitude"])
        stop.longitude = float(place["longitude"])

    routable = [stop for stop in stops if stop.resolved]
    if len(routable) < 2:
        return stops, _all_unavailable(stops), "Stop locations could not be placed on the map."

    try:
        computed = await get_route_legs([(s.latitude, s.longitude) for s in routable])  # type: ignore[arg-type]
    except RoutingUnavailable as exc:
        return stops, _all_unavailable(stops), str(exc)

    # `computed` covers consecutive *routable* stops. Map it back onto the full
    # sequence so indices line up with what the UI renders; any pair separated
    # by an unresolved stop stays explicitly unknown.
    by_pair = {
        (routable[index].index, routable[index + 1].index): leg
        for index, leg in enumerate(computed)
        if index + 1 < len(routable)
    }

    legs: list[RouteLeg] = []
    for index in range(len(stops) - 1):
        found = by_pair.get((stops[index].index, stops[index + 1].index))
        if found is None:
            legs.append(RouteLeg(index, index + 1, None, None))
        else:
            legs.append(RouteLeg(index, index + 1, found.distance_km, found.duration_minutes))
    return stops, legs, None


def _all_unavailable(stops: list[Stop]) -> list[RouteLeg]:
    return [RouteLeg(index, index + 1, None, None) for index in range(len(stops) - 1)]
