import { describe, expect, it } from 'vitest';
import { buildRecentActivity, buildTravelInsights, relativeTime } from './dashboard';
import { Booking, Trip } from '../types';

function trip(overrides: Partial<Trip> = {}): Trip {
  return {
    id: 't1',
    destination: 'Manali',
    country: 'India',
    image: '',
    startDate: '2026-12-10',
    endDate: '2026-12-14',
    travelers: 2,
    budget: 30000,
    status: 'upcoming',
    createdAt: '2026-09-20T10:00:00',
    ...overrides
  };
}

function booking(overrides: Partial<Booking> = {}): Booking {
  return {
    id: 'b1',
    reference: 'ATL-ABC123',
    title: 'Manali Package',
    type: 'Package',
    image: '',
    date: '2026-12-10',
    price: 28500,
    status: 'upcoming',
    travelers: 2,
    createdAt: '2026-09-21T10:00:00',
    ...overrides
  };
}

describe('buildRecentActivity', () => {
  it('is empty for a new account rather than showing sample entries', () => {
    expect(buildRecentActivity([], [])).toEqual([]);
  });

  it('describes real trips and bookings', () => {
    const entries = buildRecentActivity([trip()], [booking()]);
    expect(entries.map((e) => e.label)).toEqual([
    'Booking ATL-ABC123 confirmed',
    // 10 Dec to 14 Dec inclusive is five days.
    'Planned a 5-day trip to Manali']
    );
  });

  it('orders newest first', () => {
    const entries = buildRecentActivity(
      [trip({ id: 'old', createdAt: '2026-01-01T00:00:00' })],
      [booking({ id: 'new', createdAt: '2026-09-25T00:00:00' })]
    );
    expect(entries[0].id).toBe('booking-new');
  });

  it('marks a cancelled booking as cancelled', () => {
    const [entry] = buildRecentActivity([], [booking({ status: 'cancelled' })]);
    expect(entry.label).toBe('Cancelled booking ATL-ABC123');
  });

  it('skips records with no timestamp instead of inventing one', () => {
    // Seeded demo bookings have no created_at; they must not appear with a
    // made-up time.
    expect(buildRecentActivity([trip({ createdAt: undefined })], [booking({ createdAt: undefined })])).toEqual([]);
  });

  it('caps the feed', () => {
    const bookings = Array.from({ length: 9 }, (_, i) =>
    booking({ id: `b${i}`, reference: `ATL-${i}`, createdAt: `2026-09-0${i + 1}T00:00:00` })
    );
    expect(buildRecentActivity([], bookings)).toHaveLength(5);
  });
});

describe('buildTravelInsights', () => {
  it('is empty with no trips rather than showing invented preferences', () => {
    expect(buildTravelInsights([])).toEqual([]);
  });

  it('counts trips and averages their real length', () => {
    const insights = buildTravelInsights([
    trip({ id: 'a', startDate: '2026-12-10', endDate: '2026-12-14' }), // 5 days
    trip({ id: 'b', startDate: '2026-11-01', endDate: '2026-11-03' })  // 3 days
    ]);
    const byLabel = Object.fromEntries(insights.map((i) => [i.label, i.value]));
    expect(byLabel['Trips planned']).toBe('2');
    expect(byLabel['Average trip length']).toBe('4.0 days');
  });

  it('reports the month most trips actually start in', () => {
    const insights = buildTravelInsights([
    trip({ id: 'a', startDate: '2026-11-02' }),
    trip({ id: 'b', startDate: '2026-11-20' }),
    trip({ id: 'c', startDate: '2026-12-10' })
    ]);
    expect(insights.find((i) => i.label === 'Most-planned month')?.value).toBe('November');
  });

  it('only names a favourite destination once it is a repeat', () => {
    const single = buildTravelInsights([trip()]);
    expect(single.some((i) => i.label === 'Most-planned destination')).toBe(false);

    const repeated = buildTravelInsights([trip({ id: 'a' }), trip({ id: 'b' })]);
    expect(repeated.find((i) => i.label === 'Most-planned destination')?.value).toBe('Manali');
  });

  it('ignores a trip whose dates are unusable', () => {
    const insights = buildTravelInsights([trip({ startDate: 'nonsense', endDate: 'nonsense' })]);
    expect(insights.find((i) => i.label === 'Trips planned')?.value).toBe('1');
    expect(insights.some((i) => i.label === 'Average trip length')).toBe(false);
  });
});

describe('relativeTime', () => {
  const now = new Date('2026-09-28T12:00:00Z');

  it('treats a zone-less backend timestamp as UTC, not local time', () => {
    // utcnow() has no designator; parsing it as local would be hours out.
    expect(relativeTime('2026-09-28T11:00:00', now)).toBe('1 hour ago');
  });

  it.each([
  ['2026-09-28T11:59:30', 'Just now'],
  ['2026-09-28T11:30:00', '30 minutes ago'],
  ['2026-09-28T09:00:00', '3 hours ago'],
  ['2026-09-27T12:00:00', 'Yesterday'],
  ['2026-09-20T12:00:00', '8 days ago'],
  ['2026-07-28T12:00:00', '2 months ago'],
  ['2025-09-28T12:00:00', '1 year ago']])(
    'renders %s as %s',
    (iso, expected) => {
      expect(relativeTime(iso, now)).toBe(expected);
    }
  );

  it('returns nothing for an unparseable timestamp', () => {
    expect(relativeTime('not-a-date', now)).toBe('');
  });
});
