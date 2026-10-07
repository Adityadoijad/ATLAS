import { DestinationForecast, ForecastDay, Trip } from '../types';

/**
 * What the weather card should show, decided before anything is rendered.
 *
 * The card has four genuinely different states and only one of them contains
 * weather. Keeping that decision here — rather than inside JSX — is what makes
 * it testable, and the states are exhaustive so there is no path where the card
 * falls back to plausible-looking numbers.
 */

export type WeatherOutlook =
  | { kind: 'no-trip' }
  | { kind: 'loading'; destination: string }
  | { kind: 'unavailable'; destination: string; reason: string }
  | {
      kind: 'forecast';
      destination: string;
      resolvedDestination: string;
      days: ForecastDay[];
      /** True only when the provider's window actually reaches the trip dates. */
      coversTripDates: boolean;
      tripStartDate: string;
      forecastThrough: string;
    };

/**
 * The trip the dashboard's weather is about.
 *
 * The soonest trip that has not finished: one already under way beats one three
 * months out, because that is the weather the traveller is standing in. Trips
 * with unusable dates are skipped rather than sorted arbitrarily.
 */
export function relevantTripForWeather(trips: Trip[], today: Date = new Date()): Trip | null {
  const midnight = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());

  const candidates = trips.
  filter((trip) => trip.status !== 'past' && trip.destination).
  map((trip) => ({ trip, start: Date.parse(`${trip.startDate}T00:00:00Z`), end: Date.parse(`${trip.endDate}T00:00:00Z`) })).
  filter((entry) => !Number.isNaN(entry.start) && !Number.isNaN(entry.end)).
  filter((entry) => entry.end >= midnight).
  sort((a, b) => a.start - b.start);

  return candidates[0]?.trip ?? null;
}

/**
 * Fold a trip and whatever the API returned into one state.
 *
 * `forecast === undefined` means the request is still in flight; a request that
 * finished but failed arrives as a real payload with `isRealtimeData: false`,
 * which is the case that must never be mistaken for the loading state.
 */
export function weatherOutlook(
  trip: Trip | null,
  forecast: DestinationForecast | undefined
): WeatherOutlook {
  if (!trip) return { kind: 'no-trip' };
  if (!forecast) return { kind: 'loading', destination: trip.destination };

  if (!forecast.isRealtimeData || forecast.days.length === 0) {
    return {
      kind: 'unavailable',
      destination: trip.destination,
      reason: forecast.unavailableReason ?? 'Live weather unavailable'
    };
  }

  const tripDays = forecast.days.filter(
    (day) => day.date >= trip.startDate && day.date <= trip.endDate
  );
  const coversTripDates = tripDays.length > 0;

  return {
    kind: 'forecast',
    destination: trip.destination,
    resolvedDestination: forecast.resolvedDestination ?? trip.destination,
    // When the window reaches the trip, show the trip's days. Otherwise show
    // what the provider does cover, labelled as a current outlook — never the
    // trip's dates with today's numbers attached to them.
    days: coversTripDates ? tripDays : forecast.days,
    coversTripDates,
    tripStartDate: trip.startDate,
    forecastThrough: forecast.forecastThrough ?? forecast.days[forecast.days.length - 1].date
  };
}

/** "Forecast for your trip" vs "Current outlook" — stated, not implied. */
export function outlookCaption(outlook: Extract<WeatherOutlook, {kind: 'forecast';}>): string {
  if (outlook.coversTripDates) {
    return `Forecast for your travel dates in ${outlook.resolvedDestination}.`;
  }
  return `Current outlook for ${outlook.resolvedDestination}. Your travel dates are beyond the forecast window — weather for ${formatShortDate(outlook.tripStartDate)} appears closer to departure.`;
}

/** `2026-10-02` -> `2 Oct`. Date-only strings are never timezone-shifted. */
export function formatShortDate(iso: string): string {
  const parsed = new Date(`${iso}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', timeZone: 'UTC' });
}
