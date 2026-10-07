import { Booking, Trip } from '../types';

/**
 * Dashboard figures derived from persisted records only.
 *
 * Everything here is computed from trips and bookings the user actually has.
 * When there is nothing to compute from, these return empty results so the
 * dashboard can say so — a fabricated "12 trips planned" or "₹4,200 saved"
 * tells the user something untrue about their own account.
 */

export interface ActivityEntry {
  id: string;
  label: string;
  at: string;
}

export interface InsightEntry {
  label: string;
  value: string;
}

const MS_PER_DAY = 24 * 60 * 60 * 1000;

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

/**
 * The backend stores `datetime.utcnow()`, so its timestamps arrive with no
 * timezone designator. Parsing those as local time would place every event
 * hours off — "6 hours ago" for something that just happened in IST.
 */
function parseUtc(iso: string): Date {
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(hasZone ? iso : `${iso}Z`);
}

/** "2 hours ago" / "Yesterday" — from a real timestamp, never invented. */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const then = parseUtc(iso);
  if (Number.isNaN(then.getTime())) return '';

  const seconds = Math.max(0, Math.round((now.getTime() - then.getTime()) / 1000));
  if (seconds < 60) return 'Just now';

  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} ago`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;

  const days = Math.round(hours / 24);
  if (days === 1) return 'Yesterday';
  if (days < 30) return `${days} days ago`;

  const months = Math.round(days / 30);
  if (months < 12) return `${months} month${months === 1 ? '' : 's'} ago`;

  const years = Math.round(months / 12);
  return `${years} year${years === 1 ? '' : 's'} ago`;
}

function tripLengthDays(trip: Trip): number {
  const start = new Date(trip.startDate).getTime();
  const end = new Date(trip.endDate).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) return 0;
  return Math.round((end - start) / MS_PER_DAY) + 1;
}

/**
 * The user's own recent actions, newest first.
 *
 * Only records that carry a real timestamp are included. Saved places have no
 * `created_at`, so they are left out rather than given a plausible-looking one.
 */
export function buildRecentActivity(trips: Trip[], bookings: Booking[], limit = 5): ActivityEntry[] {
  const entries: ActivityEntry[] = [];

  for (const trip of trips) {
    if (!trip.createdAt) continue;
    const days = tripLengthDays(trip);
    entries.push({
      id: `trip-${trip.id}`,
      label: days > 0
        ? `Planned a ${days}-day trip to ${trip.destination}`
        : `Planned a trip to ${trip.destination}`,
      at: trip.createdAt
    });
  }

  for (const booking of bookings) {
    if (!booking.createdAt) continue;
    entries.push({
      id: `booking-${booking.id}`,
      label: booking.status === 'cancelled'
        ? `Cancelled booking ${booking.reference}`
        : `Booking ${booking.reference} confirmed`,
      at: booking.createdAt
    });
  }

  return entries.
  sort((a, b) => parseUtc(b.at).getTime() - parseUtc(a.at).getTime()).
  slice(0, limit);
}

/**
 * Patterns across the user's saved trips.
 *
 * Returns an empty list when there are no trips, so the dashboard shows an
 * honest "insights appear once you plan a trip" state instead of invented
 * preferences.
 */
export function buildTravelInsights(trips: Trip[]): InsightEntry[] {
  if (trips.length === 0) return [];

  const insights: InsightEntry[] = [
    { label: 'Trips planned', value: String(trips.length) }
  ];

  const lengths = trips.map(tripLengthDays).filter((days) => days > 0);
  if (lengths.length > 0) {
    const average = lengths.reduce((sum, days) => sum + days, 0) / lengths.length;
    insights.push({ label: 'Average trip length', value: `${average.toFixed(1)} days` });
  }

  const monthCounts = new Map<number, number>();
  for (const trip of trips) {
    const month = new Date(trip.startDate).getMonth();
    if (Number.isNaN(month)) continue;
    monthCounts.set(month, (monthCounts.get(month) ?? 0) + 1);
  }
  const topMonth = [...monthCounts.entries()].sort((a, b) => b[1] - a[1])[0];
  if (topMonth) {
    insights.push({ label: 'Most-planned month', value: MONTHS[topMonth[0]] });
  }

  const destinationCounts = new Map<string, number>();
  for (const trip of trips) {
    if (!trip.destination) continue;
    destinationCounts.set(trip.destination, (destinationCounts.get(trip.destination) ?? 0) + 1);
  }
  const topDestination = [...destinationCounts.entries()].sort((a, b) => b[1] - a[1])[0];
  // Only worth showing once it is a repeat, otherwise it just restates the
  // single trip above it.
  if (topDestination && topDestination[1] > 1) {
    insights.push({ label: 'Most-planned destination', value: topDestination[0] });
  }

  return insights;
}
