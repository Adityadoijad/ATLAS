import { ItineraryDay } from '../types';

/**
 * Google Maps hand-off for the itinerary route card.
 *
 * Uses the universal Maps URL scheme (https://developers.google.com/maps/documentation/urls),
 * which needs no API key and no SDK — the link is built entirely in the browser
 * from data ATLAS already has.
 *
 * On precision: the planner does not produce coordinates per stop. The Route
 * agent geocodes the destination city only, and itinerary activities carry a
 * place *name*. So stops are sent as text, qualified with the destination city
 * to keep "Mall Road" from resolving to a different country. If per-stop
 * coordinates are ever added, pass them here instead — Maps accepts
 * "lat,lng" wherever it accepts a name.
 */

/**
 * The Maps URL scheme accepts at most 9 waypoints between origin and
 * destination. A longer trip is truncated rather than producing a URL Maps
 * would reject outright.
 */
export const MAX_ROUTE_STOPS = 10;

/** Arrows the planner sometimes uses to pack a whole leg into one location. */
const LEG_SEPARATOR = /\s*(?:→|->|—>)\s*/;

function splitLegs(location: string): string[] {
  return location.split(LEG_SEPARATOR).map((part) => part.trim()).filter(Boolean);
}

/**
 * Add the destination city unless the stop already names it.
 *
 * "Hadimba Temple" is ambiguous worldwide; "Hadimba Temple, Manali" is not.
 */
export function qualifyStop(location: string, destination: string): string {
  const stop = location.trim();
  const city = destination.trim();
  if (!stop) return '';
  if (!city || stop.toLowerCase().includes(city.toLowerCase())) return stop;
  return `${stop}, ${city}`;
}

/**
 * The ordered, mappable stops of a trip, taken from the itinerary activities.
 *
 * Consecutive repeats collapse — a hotel appearing as both the night's stay
 * and the next morning's breakfast is one place to drive to, not two. A
 * non-consecutive repeat is kept, because returning to the hotel later in the
 * trip is a real leg of the route.
 */
export function routeStopsFromDays(days: ItineraryDay[], destination: string): string[] {
  const stops: string[] = [];
  for (const day of days) {
    for (const item of day.items) {
      for (const leg of splitLegs(item.location ?? '')) {
        const stop = qualifyStop(leg, destination);
        if (!stop) continue;
        if (stops.length > 0 && stops[stops.length - 1].toLowerCase() === stop.toLowerCase()) continue;
        stops.push(stop);
      }
    }
  }
  return stops;
}

/**
 * The stops a Maps link can actually carry: blanks and consecutive repeats
 * removed, then truncated to the URL scheme's limit while keeping the real
 * destination.
 *
 * Exported so the route card can list exactly the stops the link will open —
 * showing one route and opening a different one would be worse than showing
 * none.
 */
export function limitRouteStops(stops: string[]): string[] {
  const cleaned: string[] = [];
  for (const raw of stops) {
    const stop = (raw ?? '').trim();
    if (!stop) continue;
    if (cleaned.length > 0 && cleaned[cleaned.length - 1].toLowerCase() === stop.toLowerCase()) continue;
    cleaned.push(stop);
  }
  if (cleaned.length <= MAX_ROUTE_STOPS) return cleaned;
  // Keep the end of the trip: it matters more than a middle stop that got cut.
  return [...cleaned.slice(0, MAX_ROUTE_STOPS - 1), cleaned[cleaned.length - 1]];
}

/**
 * Build a Google Maps directions URL, or null when there is not enough route
 * to show.
 *
 * Returns null rather than a half-formed link for fewer than two distinct
 * stops — the caller hides the CTA instead of opening a broken map. Every
 * value goes through URLSearchParams, so names with spaces, commas, ampersands
 * or non-Latin characters are escaped correctly; nothing is concatenated raw.
 */
export function buildGoogleMapsDirectionsUrl(stops: string[]): string | null {
  const limited = limitRouteStops(stops);
  if (limited.length < 2) return null;

  const params = new URLSearchParams({
    api: '1',
    origin: limited[0],
    destination: limited[limited.length - 1],
    travelmode: 'driving'
  });

  const waypoints = limited.slice(1, -1);
  // Omitted entirely for a two-stop route — an empty waypoints parameter makes
  // Maps drop the whole request.
  if (waypoints.length > 0) {
    params.set('waypoints', waypoints.join('|'));
  }

  return `https://www.google.com/maps/dir/?${params.toString()}`;
}
