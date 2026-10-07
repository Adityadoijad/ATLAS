import { describe, expect, it } from 'vitest';
import {
  formatShortDate,
  outlookCaption,
  relevantTripForWeather,
  weatherOutlook } from
'./weatherOutlook';
import { DestinationForecast, ForecastDay, Trip } from '../types';

function trip(overrides: Partial<Trip> = {}): Trip {
  return {
    id: 't1',
    destination: 'Manali',
    country: 'India',
    image: '',
    startDate: '2026-10-02',
    endDate: '2026-10-05',
    travelers: 2,
    budget: 30000,
    status: 'upcoming',
    ...overrides
  };
}

function day(date: string, overrides: Partial<ForecastDay> = {}): ForecastDay {
  return {
    date,
    weekday: new Date(`${date}T00:00:00Z`).toLocaleDateString('en-IN', { weekday: 'short', timeZone: 'UTC' }),
    temperatureC: 22,
    temperatureMinC: 18,
    temperatureMaxC: 26,
    condition: 'light rain',
    icon: '10d',
    stepCount: 8,
    localTimeOfSummary: '11:30',
    ...overrides
  };
}

function forecast(overrides: Partial<DestinationForecast> = {}): DestinationForecast {
  return {
    destination: 'Manali',
    isRealtimeData: true,
    resolvedDestination: 'Manali, IN',
    latitude: 32.24,
    longitude: 77.19,
    localDate: '2026-10-01',
    forecastThrough: '2026-10-05',
    days: [day('2026-10-01'), day('2026-10-02'), day('2026-10-03'), day('2026-10-04'), day('2026-10-05')],
    unavailableReason: null,
    ...overrides
  };
}

describe('relevantTripForWeather', () => {
  const today = new Date('2026-10-01T09:00:00Z');

  it('has nothing to show weather for on a new account', () => {
    expect(relevantTripForWeather([], today)).toBeNull();
  });

  it('picks the soonest trip that has not finished', () => {
    const chosen = relevantTripForWeather(
      [
      trip({ id: 'later', startDate: '2026-12-01', endDate: '2026-12-05' }),
      trip({ id: 'sooner', startDate: '2026-10-10', endDate: '2026-10-14' })],

      today
    );
    expect(chosen?.id).toBe('sooner');
  });

  it('prefers a trip already under way over one further out', () => {
    // The weather a traveller is standing in matters more than December's.
    const chosen = relevantTripForWeather(
      [
      trip({ id: 'future', startDate: '2026-11-01', endDate: '2026-11-04' }),
      trip({ id: 'current', startDate: '2026-09-29', endDate: '2026-10-03' })],

      today
    );
    expect(chosen?.id).toBe('current');
  });

  it('ignores trips that have already ended', () => {
    expect(
      relevantTripForWeather([trip({ startDate: '2026-08-01', endDate: '2026-08-05' })], today)
    ).toBeNull();
  });

  it('includes a trip that ends today rather than dropping it mid-trip', () => {
    const chosen = relevantTripForWeather(
      [trip({ id: 'ends-today', startDate: '2026-09-28', endDate: '2026-10-01' })],
      today
    );
    expect(chosen?.id).toBe('ends-today');
  });

  it('ignores trips marked past even if their dates say otherwise', () => {
    expect(relevantTripForWeather([trip({ status: 'past' })], today)).toBeNull();
  });

  it('skips a trip with unusable dates instead of ordering it arbitrarily', () => {
    const chosen = relevantTripForWeather(
      [trip({ id: 'broken', startDate: 'nonsense', endDate: 'nonsense' }), trip({ id: 'valid' })],
      today
    );
    expect(chosen?.id).toBe('valid');
  });

  it('skips a trip with no destination, which cannot be looked up', () => {
    expect(relevantTripForWeather([trip({ destination: '' })], today)).toBeNull();
  });
});

describe('weatherOutlook', () => {
  it('reports no trip when there is none — the empty state, not weather', () => {
    expect(weatherOutlook(null, forecast())).toEqual({ kind: 'no-trip' });
  });

  it('distinguishes a request in flight from a request that failed', () => {
    expect(weatherOutlook(trip(), undefined)).toEqual({ kind: 'loading', destination: 'Manali' });
  });

  it('shows the trip own dates when the provider window reaches them', () => {
    const outlook = weatherOutlook(trip({ startDate: '2026-10-03', endDate: '2026-10-04' }), forecast());
    expect(outlook.kind).toBe('forecast');
    if (outlook.kind !== 'forecast') return;
    expect(outlook.coversTripDates).toBe(true);
    expect(outlook.days.map((d) => d.date)).toEqual(['2026-10-03', '2026-10-04']);
  });

  it('never attributes the returned days to travel dates outside the window', () => {
    // The core fabrication this guards against: October's numbers printed
    // under December's dates.
    const outlook = weatherOutlook(trip({ startDate: '2026-12-20', endDate: '2026-12-24' }), forecast());
    expect(outlook.kind).toBe('forecast');
    if (outlook.kind !== 'forecast') return;
    expect(outlook.coversTripDates).toBe(false);
    expect(outlook.days.map((d) => d.date)).not.toContain('2026-12-20');
    expect(outlookCaption(outlook)).toContain('beyond the forecast window');
  });

  it('says so in words when the forecast does cover the trip', () => {
    const outlook = weatherOutlook(trip({ startDate: '2026-10-03', endDate: '2026-10-04' }), forecast());
    if (outlook.kind !== 'forecast') throw new Error('expected a forecast');
    expect(outlookCaption(outlook)).toBe('Forecast for your travel dates in Manali, IN.');
  });

  it('shows unavailable with the reason when live weather failed', () => {
    const outlook = weatherOutlook(
      trip(),
      forecast({
        isRealtimeData: false,
        days: [],
        unavailableReason: 'The configured OpenWeatherMap API key was rejected.'
      })
    );
    expect(outlook).toEqual({
      kind: 'unavailable',
      destination: 'Manali',
      reason: 'The configured OpenWeatherMap API key was rejected.'
    });
  });

  it('treats a live response with no days as unavailable, not as an empty forecast', () => {
    const outlook = weatherOutlook(trip(), forecast({ days: [] }));
    expect(outlook.kind).toBe('unavailable');
  });

  it('always has a reason to show, even when the backend sent none', () => {
    const outlook = weatherOutlook(trip(), forecast({ isRealtimeData: false, days: [], unavailableReason: null }));
    if (outlook.kind !== 'unavailable') throw new Error('expected unavailable');
    expect(outlook.reason).toBe('Live weather unavailable');
  });

  it('labels the numbers with the place the provider resolved, not the spelling asked for', () => {
    const outlook = weatherOutlook(trip({ destination: 'manali himachal' }), forecast());
    if (outlook.kind !== 'forecast') throw new Error('expected a forecast');
    expect(outlook.resolvedDestination).toBe('Manali, IN');
  });

  it('falls back to the requested name when the provider named nothing', () => {
    const outlook = weatherOutlook(trip(), forecast({ resolvedDestination: null }));
    if (outlook.kind !== 'forecast') throw new Error('expected a forecast');
    expect(outlook.resolvedDestination).toBe('Manali');
  });
});

describe('formatShortDate', () => {
  it('does not shift a date-only string across a timezone boundary', () => {
    // Parsed as local time, 2026-10-02 becomes 1 Oct for anyone west of UTC.
    expect(formatShortDate('2026-10-02')).toBe('2 Oct');
  });

  it('returns the input unchanged when it is not a date', () => {
    expect(formatShortDate('nonsense')).toBe('nonsense');
  });
});
