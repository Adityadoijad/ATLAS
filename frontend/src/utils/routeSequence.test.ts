import { describe, expect, it } from 'vitest';
import {
  arrivalLeg,
  formatDistance,
  formatDuration,
  formatLeg,
  itineraryStopLabels,
  routeIndexByRow,
  travelLabel } from
'./routeSequence';
import { ItineraryDay, ItineraryItem, RouteLeg, TripRoute } from '../types';

function item(overrides: Partial<ItineraryItem> = {}): ItineraryItem {
  return {
    time: '09:00',
    title: 'Arrive',
    location: 'Udaipur City Railway Station',
    duration: 'Flexible',
    cost: 300,
    kind: 'travel',
    ...overrides
  };
}

function day(items: ItineraryItem[], overrides: Partial<ItineraryDay> = {}): ItineraryDay {
  return {
    day_number: 1,
    day: 1,
    title: 'Day 1',
    date: '2026-12-10',
    activities: [],
    items,
    ...overrides
  };
}

function leg(overrides: Partial<RouteLeg> = {}): RouteLeg {
  return {
    fromIndex: 0,
    toIndex: 1,
    distanceKm: 3.8,
    durationMinutes: 14,
    routingAvailable: true,
    ...overrides
  };
}

function route(overrides: Partial<TripRoute> = {}): TripRoute {
  return {
    tripId: 't1',
    stops: [
    { index: 0, label: 'Nagpur Railway Station', query: 'Nagpur Railway Station', latitude: 21.1, longitude: 79.0, isBoarding: true, resolved: true },
    { index: 1, label: 'Udaipur City Railway Station', query: 'Udaipur City Railway Station', latitude: 24.5, longitude: 73.7, isBoarding: false, resolved: true },
    { index: 2, label: 'Lake City Heritage Hotel', query: 'Lake City Heritage Hotel, Udaipur', latitude: 24.58, longitude: 73.69, isBoarding: false, resolved: true }],

    legs: [leg({ fromIndex: 0, toIndex: 1 }), leg({ fromIndex: 1, toIndex: 2, distanceKm: 4.2, durationMinutes: 25 })],
    unavailableReason: null,
    ...overrides
  };
}

describe('itineraryStopLabels', () => {
  it('collapses a consecutive repeat but keeps a return visit', () => {
    // The hotel is one place to drive to on arrival, and a real journey back
    // to it the next morning.
    const labels = itineraryStopLabels([
    day([item({ location: 'Station' }), item({ location: 'Hotel' }), item({ location: 'Hotel' })]),
    day([item({ location: 'Lake' }), item({ location: 'Hotel' })])]
    );
    expect(labels).toEqual(['Station', 'Hotel', 'Lake', 'Hotel']);
  });

  it('skips items with no location rather than emitting a blank stop', () => {
    expect(itineraryStopLabels([day([item({ location: '' }), item({ location: 'Lake' })])])).toEqual(['Lake']);
  });
});

describe('routeIndexByRow', () => {
  it('maps each row to its own position in the canonical route', () => {
    const days = [day([item({ location: 'Udaipur City Railway Station' }), item({ location: 'Lake City Heritage Hotel' })])];
    const byRow = routeIndexByRow(days, route());
    // Stop 0 is the boarding location, so itinerary rows start at 1.
    expect(byRow.get('0:0')).toBe(1);
    expect(byRow.get('0:1')).toBe(2);
  });

  it('gives a place visited twice each arrival separately', () => {
    // The regression: matching by label handed the second visit to the hotel
    // the first visit's leg — an 863 km train journey on a two-minute walk.
    const days = [day([
    item({ location: 'Udaipur City Railway Station' }),
    item({ location: 'Lake City Heritage Hotel' }),
    item({ location: 'Udaipur City Railway Station' })])
    ];
    const withReturn = route({
      stops: [
      { index: 0, label: 'Nagpur Railway Station', query: 'q', latitude: 21, longitude: 79, isBoarding: true, resolved: true },
      { index: 1, label: 'Udaipur City Railway Station', query: 'q', latitude: 24, longitude: 73, isBoarding: false, resolved: true },
      { index: 2, label: 'Lake City Heritage Hotel', query: 'q', latitude: 24, longitude: 73, isBoarding: false, resolved: true },
      { index: 3, label: 'Udaipur City Railway Station', query: 'q', latitude: 24, longitude: 73, isBoarding: false, resolved: true }],

      legs: [
      leg({ fromIndex: 0, toIndex: 1, distanceKm: 863, durationMinutes: 650 }),
      leg({ fromIndex: 1, toIndex: 2, distanceKm: 7.8, durationMinutes: 11 }),
      leg({ fromIndex: 2, toIndex: 3, distanceKm: 6.9, durationMinutes: 10 })]

    });

    const byRow = routeIndexByRow(days, withReturn);
    expect(byRow.get('0:0')).toBe(1);
    expect(byRow.get('0:2')).toBe(3);
    expect(arrivalLeg(withReturn, byRow.get('0:2'))?.distanceKm).toBe(6.9);
    expect(arrivalLeg(withReturn, byRow.get('0:0'))?.distanceKm).toBe(863);
  });

  it('points a consecutive repeat at the stop already consumed', () => {
    // The hotel as both the night stay and the next morning's breakfast is one
    // arrival, not two.
    const days = [day([
    item({ location: 'Udaipur City Railway Station' }),
    item({ location: 'Lake City Heritage Hotel' }),
    item({ location: 'Lake City Heritage Hotel' })])
    ];
    const byRow = routeIndexByRow(days, route());
    expect(byRow.get('0:1')).toBe(2);
    expect(byRow.get('0:2')).toBe(2);
  });

  it('starts at stop 0 for a trip with no boarding location', () => {
    const legacy = route();
    legacy.stops[0].isBoarding = false;
    const days = [day([item({ location: 'Nagpur Railway Station' })])];
    expect(routeIndexByRow(days, legacy).get('0:0')).toBe(0);
  });

  it('is empty while the route has not loaded', () => {
    expect(routeIndexByRow([day([item()])], undefined).size).toBe(0);
  });
});

describe('arrivalLeg', () => {
  it('finds the leg arriving at a stop', () => {
    expect(arrivalLeg(route(), 1)?.distanceKm).toBe(3.8);
  });

  it('has nothing arriving at the origin', () => {
    // Nothing precedes the start of the journey.
    expect(arrivalLeg(route(), 0)).toBeUndefined();
  });

  it('returns nothing for a missing route or index', () => {
    expect(arrivalLeg(undefined, 1)).toBeUndefined();
    expect(arrivalLeg(route(), undefined)).toBeUndefined();
  });
});

describe('formatLeg', () => {
  it('renders duration before distance', () => {
    expect(formatLeg(leg())).toBe('14 min · 3.8 km');
  });

  it('returns null rather than a number when routing was unavailable', () => {
    expect(formatLeg(leg({ routingAvailable: false, distanceKm: null, durationMinutes: null }))).toBeNull();
  });

  it('returns null when a leg claims availability but carries no numbers', () => {
    // Defensive: a malformed payload must not render "null km".
    expect(formatLeg(leg({ distanceKm: null }))).toBeNull();
  });

  it('returns null for a missing leg', () => {
    expect(formatLeg(undefined)).toBeNull();
  });

  it('renders a genuine zero-distance leg, which is a real answer', () => {
    // Two stops at the same address really are 0 km apart. The rule is that
    // *unknown* must not be zero — not that zero can never be shown.
    expect(formatLeg(leg({ distanceKm: 0, durationMinutes: 0 }))).toBe('0 min · 0 m');
  });
});

describe('formatDuration', () => {
  it.each([
  [14, '14 min'],
  [59, '59 min'],
  [60, '1 h'],
  [135, '2 h 15 min'],
  [600, '10 h']])(
    'renders %i minutes as %s',
    (minutes, expected) => {
      expect(formatDuration(minutes)).toBe(expected);
    }
  );
});

describe('formatDistance', () => {
  it('uses metres below a kilometre', () => {
    expect(formatDistance(0.4)).toBe('400 m');
  });

  it('uses one decimal place above a kilometre', () => {
    expect(formatDistance(3.84)).toBe('3.8 km');
  });
});

describe('travelLabel', () => {
  it('distinguishes still-loading from genuinely unavailable', () => {
    expect(travelLabel(undefined, false)).toEqual({ text: 'Calculating travel time…', available: false });
    expect(travelLabel(undefined, true)).toEqual({ text: 'Travel time unavailable', available: false });
  });

  it('shows real travel data once it is available', () => {
    expect(travelLabel(leg(), true)).toEqual({ text: '14 min · 3.8 km', available: true });
  });

  it('never renders "0 km" as a stand-in for missing data', () => {
    // The regression this whole feature replaces.
    const states = [
    travelLabel(undefined, false),
    travelLabel(undefined, true),
    travelLabel(leg({ routingAvailable: false, distanceKm: null, durationMinutes: null }), true)];

    for (const state of states) {
      expect(state?.text).not.toContain('0 km');
      expect(state?.available).toBe(false);
    }
  });
});

describe('origin row', () => {
  it('says the journey starts here rather than reporting a failure', () => {
    // The boarding row has no arriving leg because nothing precedes it.
    // "Travel time unavailable" there would imply something broke.
    expect(travelLabel(undefined, true, true)).toEqual({ text: 'Journey starts here', available: true });
  });

  it('still says that before the route has loaded', () => {
    expect(travelLabel(undefined, false, true)?.text).toBe('Journey starts here');
  });
});

describe('rows beyond the backend stop cap', () => {
  it('leaves them unmapped rather than borrowing another stop leg', () => {
    // The backend truncates long trips. A row past the cap has no stop, and
    // pointing it at the last mapped one put the previous stop's distance on
    // an unrelated afternoon.
    const days = [day([
    item({ location: 'Udaipur City Railway Station' }),
    item({ location: 'Lake City Heritage Hotel' }),
    item({ location: 'Beyond The Cap' }),
    item({ location: 'Beyond The Cap' })])
    ];

    const byRow = routeIndexByRow(days, route()); // three stops only
    expect(byRow.get('0:0')).toBe(1);
    expect(byRow.get('0:1')).toBe(2);
    expect(byRow.get('0:2')).toBeUndefined();
    expect(byRow.get('0:3')).toBeUndefined();
    // And so the row reports honestly rather than showing a wrong distance.
    expect(travelLabel(arrivalLeg(route(), byRow.get('0:2')), true)?.text).toBe('Travel time unavailable');
  });
});
