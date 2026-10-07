import { ItineraryDay, RouteLeg, TripRoute } from '../types';

/**
 * Mapping the backend's canonical route onto what the itinerary renders.
 *
 * The backend owns the ordered stop list — boarding location first, then every
 * itinerary stop — so the timeline and the map cannot disagree about where the
 * trip starts. This module only answers "which leg belongs to this row".
 *
 * The rule throughout: an unknown distance is absent, never zero. `0 km` is a
 * real answer meaning two stops are the same place, so using it for "we could
 * not find out" tells the traveller a journey takes no time at all.
 */

/**
 * Stop labels in the same order the backend builds them, minus the boarding
 * location.
 *
 * Consecutive repeats collapse — a hotel that is both the night's stay and the
 * next morning's breakfast is one place to travel to. This mirrors
 * `build_sequence` in `services/route_sequence.py`; the two must agree, which
 * is why the itinerary rows are matched by label rather than by position.
 */
export function itineraryStopLabels(days: ItineraryDay[]): string[] {
  const labels: string[] = [];
  for (const day of days) {
    for (const item of day.items) {
      const label = (item.location ?? '').trim();
      if (!label) continue;
      if (labels.length > 0 && labels[labels.length - 1].toLowerCase() === label.toLowerCase()) continue;
      labels.push(label);
    }
  }
  return labels;
}

/**
 * The route stop index for each itinerary row, keyed by "dayIndex:itemIndex".
 *
 * Positional, not by name. An itinerary returns to the same hotel four times,
 * and those are four different arrivals with four different distances —
 * matching on the label alone hands every one of them the first visit's leg,
 * which puts an 863 km train journey on a row that was a two-minute walk.
 *
 * This replays the same consecutive-dedupe the backend uses in
 * `build_sequence`, offset by the boarding stop when the trip has one, so the
 * indices line up with the canonical sequence rather than being re-derived
 * from it.
 */
export function routeIndexByRow(days: ItineraryDay[], route: TripRoute | undefined): Map<string, number> {
  const byRow = new Map<string, number>();
  if (!route || route.stops.length === 0) return byRow;

  // Stop 0 is the boarding location when there is one; itinerary rows start
  // after it.
  const hasBoarding = route.stops[0]?.isBoarding === true;
  let cursor = hasBoarding ? 1 : 0;
  let previous: string | null = hasBoarding ? route.stops[0].label.trim().toLowerCase() : null;

  days.forEach((day, dayIndex) => {
    day.items.forEach((item, itemIndex) => {
      const label = (item.location ?? '').trim();
      if (!label) return;
      const key = label.toLowerCase();

      // A consecutive repeat is the same stop, so the row points at the stop
      // already consumed rather than advancing past it. Only when that stop
      // exists: past the backend's cap there is nothing to point at, and
      // reusing the last mapped index would put the previous stop's distance
      // on an unrelated row.
      if (previous !== null && sameStop(previous, key)) {
        if (cursor > 0 && cursor <= route.stops.length) {
          byRow.set(`${dayIndex}:${itemIndex}`, cursor - 1);
        }
        return;
      }
      if (cursor < route.stops.length) {
        byRow.set(`${dayIndex}:${itemIndex}`, cursor);
      }
      // The cursor advances either way, so a row beyond the cap stays
      // unmapped rather than silently borrowing a later stop's leg.
      cursor += 1;
      previous = key;
    });
  });

  return byRow;
}

/**
 * Whether two labels name the same stop, matching the backend's `_same_place`.
 * Containment, because the planner writes "Nagpur Railway Station" in one row
 * and a longer form of it in another.
 */
function sameStop(left: string, right: string): boolean {
  if (!left || !right) return false;
  return left === right || left.includes(right) || right.includes(left);
}

/** The leg arriving at a given route stop, if one was computed. */
export function arrivalLeg(route: TripRoute | undefined, stopIndex: number | undefined): RouteLeg | undefined {
  if (!route || stopIndex === undefined) return undefined;
  return route.legs.find((leg) => leg.toIndex === stopIndex);
}

/** `14 min · 3.8 km`, or null when there is nothing truthful to show. */
export function formatLeg(leg: RouteLeg | undefined): string | null {
  if (!leg || !leg.routingAvailable) return null;
  if (leg.distanceKm === null || leg.durationMinutes === null) return null;
  return `${formatDuration(leg.durationMinutes)} · ${formatDistance(leg.distanceKm)}`;
}

/** Minutes to `45 min` / `2 h 15 min`, because "135 min" is not how people think. */
export function formatDuration(minutes: number): string {
  const total = Math.max(0, Math.round(minutes));
  if (total < 60) return `${total} min`;
  const hours = Math.floor(total / 60);
  const rest = total % 60;
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`;
}

/** Sub-kilometre hops read better in metres than as `0.4 km`. */
export function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(1)} km`;
}

/**
 * What a row should show for travel: a real leg, or an explicit unavailable
 * state. Never a fabricated number and never a silent blank that reads as zero.
 */
export function travelLabel(
  leg: RouteLeg | undefined,
  routeLoaded: boolean,
  isOrigin = false
): {text: string; available: boolean;} | null {
  // The first stop has no arriving leg because nothing precedes it. That is
  // not a routing failure, and labelling it "unavailable" would suggest
  // something went wrong with a row that is simply the start of the journey.
  if (isOrigin) return { text: 'Journey starts here', available: true };
  if (!routeLoaded) return { text: 'Calculating travel time…', available: false };
  const formatted = formatLeg(leg);
  if (formatted) return { text: formatted, available: true };
  return { text: 'Travel time unavailable', available: false };
}

/** The label of the stop the whole route originates from, if the trip has one. */
export function originStopLabel(route: TripRoute | undefined): string | null {
  const first = route?.stops.find((stop) => stop.index === 0);
  return first?.isBoarding ? first.label : null;
}
