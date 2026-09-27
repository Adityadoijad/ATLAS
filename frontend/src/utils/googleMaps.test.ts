import { describe, expect, it } from 'vitest';
import {
  MAX_ROUTE_STOPS,
  buildGoogleMapsDirectionsUrl,
  qualifyStop,
  routeStopsFromDays } from
'./googleMaps';
import { ItineraryDay } from '../types';

/** Read the query parameters back out, decoded, so assertions test meaning. */
function params(url: string) {
  return Object.fromEntries(new URL(url).searchParams.entries());
}

/** Build a URL and fail the test (rather than assert non-null) if it is null. */
function urlFor(stops: string[]): string {
  const url = buildGoogleMapsDirectionsUrl(stops);
  if (url === null) throw new Error(`Expected a directions URL for ${JSON.stringify(stops)}`);
  return url;
}

function day(locations: string[], dayNumber = 1): ItineraryDay {
  return {
    day_number: dayNumber,
    day: dayNumber,
    date: '2026-12-10',
    title: `Day ${dayNumber}`,
    activities: [],
    items: locations.map((location) => ({
      time: '09:00',
      title: 'Activity',
      location,
      duration: 'Flexible',
      cost: 0,
      rating: 0,
      distanceKm: 0,
      kind: 'activity' as const
    }))
  };
}

describe('buildGoogleMapsDirectionsUrl', () => {
  // Case 1 — two stops: origin → destination, no waypoints parameter at all.
  it('builds an origin/destination route with no waypoints', () => {
    const url = urlFor(['Bhuntar Airport', 'Hotel Mountain View']);

    expect(url.startsWith('https://www.google.com/maps/dir/?')).toBe(true);
    expect(params(url)).toEqual({
      api: '1',
      origin: 'Bhuntar Airport',
      destination: 'Hotel Mountain View',
      travelmode: 'driving'
    });
    // An empty waypoints parameter makes Maps drop the request.
    expect(url).not.toContain('waypoints');
  });

  // Case 2 — the full example route from the itinerary card.
  it('puts intermediate stops in waypoints, in order', () => {
    const url = urlFor([
    'Bhuntar Airport',
    'Hotel Mountain View',
    'Heritage Walk',
    'Johnson\'s Cafe']
    );

    const query = params(url);
    expect(query.origin).toBe('Bhuntar Airport');
    expect(query.destination).toBe("Johnson's Cafe");
    expect(query.waypoints).toBe('Hotel Mountain View|Heritage Walk');
  });

  // Case 3 — not enough route to map.
  it.each([
  ['no stops', []],
  ['a single stop', ['Bhuntar Airport']],
  ['a stop plus blanks', ['Bhuntar Airport', '   ', '']],
  ['only blanks', ['', '  ']],
  ['the same place twice', ['Mall Road, Manali', 'mall road, manali']]])(
    'returns null for %s rather than a broken URL',
    (_label, stops) => {
      expect(buildGoogleMapsDirectionsUrl(stops as string[])).toBeNull();
    }
  );

  // Case 4 — characters that would corrupt a hand-concatenated URL.
  it('escapes spaces, commas, ampersands and non-Latin text', () => {
    const origin = 'Café Ñandú & Co, Road #7';
    const destination = 'हडिंबा मंदिर, मनाली';
    const waypoint = 'A/B Block, 50% Off Plaza?';
    const url = urlFor([origin, waypoint, destination]);

    // Raw separators must never appear unescaped in the query string.
    expect(url).not.toContain('&Co');
    expect(url).not.toContain('#7');
    expect(url).not.toContain('Off Plaza?');
    // …and they must survive a round trip intact.
    const query = params(url);
    expect(query.origin).toBe(origin);
    expect(query.destination).toBe(destination);
    expect(query.waypoints).toBe(waypoint);
  });

  // Case 5 — multiple waypoints, including the Maps URL limit.
  it('keeps every waypoint when the route fits', () => {
    const stops = ['Start', 'W1', 'W2', 'W3', 'W4', 'End'];
    expect(params(urlFor(stops)).waypoints).toBe('W1|W2|W3|W4');
  });

  it('truncates an over-long route but keeps the real destination', () => {
    const stops = Array.from({ length: 15 }, (_, i) => `Stop ${i + 1}`);
    const query = params(urlFor(stops));

    expect(query.origin).toBe('Stop 1');
    // The end of the trip is preserved, not silently replaced by a mid-route stop.
    expect(query.destination).toBe('Stop 15');
    // Maps accepts at most 9 waypoints.
    expect(query.waypoints.split('|')).toHaveLength(MAX_ROUTE_STOPS - 2);
    expect(query.waypoints.split('|')[0]).toBe('Stop 2');
  });

  it('collapses consecutive repeats of the same place', () => {
    const query = params(urlFor([
    'Hotel Snow Valley, Manali',
    'Hotel Snow Valley, Manali',
    'Hadimba Temple, Manali']
    ));
    expect(query.origin).toBe('Hotel Snow Valley, Manali');
    expect(query.destination).toBe('Hadimba Temple, Manali');
    expect(query.waypoints).toBeUndefined();
  });
});

describe('qualifyStop', () => {
  it('appends the destination city to an ambiguous place name', () => {
    expect(qualifyStop('Mall Road', 'Manali')).toBe('Mall Road, Manali');
  });

  it('does not repeat a city the stop already names', () => {
    expect(qualifyStop('Hotel Snow Valley, Manali', 'Manali')).toBe('Hotel Snow Valley, Manali');
    expect(qualifyStop('old manali market', 'Manali')).toBe('old manali market');
  });

  it('handles a missing destination without leaving a dangling comma', () => {
    expect(qualifyStop('Mall Road', '')).toBe('Mall Road');
  });
});

describe('routeStopsFromDays', () => {
  it('reads stops from itinerary activities across every day, in order', () => {
    const stops = routeStopsFromDays(
      [day(['Manali Bus Stand', 'Hotel Snow Valley']), day(['Solang Valley'], 2)],
      'Manali'
    );
    expect(stops).toEqual([
    // Already names the city, so it is not qualified twice.
    'Manali Bus Stand',
    'Hotel Snow Valley, Manali',
    'Solang Valley, Manali']
    );
  });

  it('splits a leg the planner packed into one location with arrows', () => {
    const stops = routeStopsFromDays([day(['Manali Bus Stand → Hotel Mountain View → Hadimba Temple'])], 'Manali');
    expect(stops).toEqual([
    'Manali Bus Stand',
    'Hotel Mountain View, Manali',
    'Hadimba Temple, Manali']
    );
  });

  it('qualifies an out-of-city travel origin with the destination too', () => {
    // Known limitation, pinned here so it is a decision rather than a surprise:
    // an inbound leg's origin gets the destination city appended. Google still
    // resolves the well-known place, and the alternative — leaving every bare
    // stop unqualified — would send "Mall Road" to an arbitrary city.
    expect(routeStopsFromDays([day(['Delhi Airport'])], 'Manali')).toEqual(['Delhi Airport, Manali']);
  });

  it('collapses a hotel that ends one day and starts the next', () => {
    const stops = routeStopsFromDays(
      [day(['Hotel Snow Valley']), day(['Hotel Snow Valley', 'Hadimba Temple'], 2)],
      'Manali'
    );
    expect(stops).toEqual(['Hotel Snow Valley, Manali', 'Hadimba Temple, Manali']);
  });

  it('keeps a genuine return to an earlier place', () => {
    const stops = routeStopsFromDays([day(['Hotel', 'Hadimba Temple', 'Hotel'])], 'Manali');
    expect(stops).toHaveLength(3);
  });

  it('skips blank locations and returns an empty route for an empty itinerary', () => {
    expect(routeStopsFromDays([day(['', '   '])], 'Manali')).toEqual([]);
    expect(routeStopsFromDays([], 'Manali')).toEqual([]);
  });

  it('produces a route a two-stop day can actually map', () => {
    const stops = routeStopsFromDays([day(['Manali Bus Stand', 'Hotel Snow Valley'])], 'Manali');
    expect(buildGoogleMapsDirectionsUrl(stops)).not.toBeNull();
  });
});
