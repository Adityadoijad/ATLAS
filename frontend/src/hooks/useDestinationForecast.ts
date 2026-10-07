import { useEffect, useState } from 'react';
import { DestinationForecast } from '../types';
import { fetchDestinationForecast } from '../services/atlasApi';

/**
 * Live weather for one destination, via ATLAS's own API.
 *
 * `undefined` means the request has not finished. A finished-but-failed request
 * resolves to a payload with `isRealtimeData: false`, so the caller can tell
 * "still loading" from "there is no weather" — conflating those is what makes a
 * UI quietly show stale or invented numbers.
 *
 * Passing `null` for the destination means there is nothing to look up (no
 * trip yet), and no request is made.
 */
export function useDestinationForecast(destination: string | null): DestinationForecast | undefined {
  const [forecast, setForecast] = useState<DestinationForecast | undefined>(undefined);

  useEffect(() => {
    if (!destination) {
      setForecast(undefined);
      return;
    }

    const token = localStorage.getItem('atlas_access_token');
    if (!token) {
      setForecast({
        destination,
        isRealtimeData: false,
        resolvedDestination: null,
        latitude: null,
        longitude: null,
        localDate: null,
        forecastThrough: null,
        days: [],
        unavailableReason: 'Sign in to see live weather for your destination.'
      });
      return;
    }

    let active = true;
    // Cleared on destination change so the previous city's days can never be
    // shown under a new heading while the new request is in flight.
    setForecast(undefined);

    fetchDestinationForecast(destination, token).
    then((data) => {
      if (active) setForecast(data);
    }).
    catch(() => {
      if (!active) return;
      // Transport failure — the endpoint itself reports provider problems as a
      // 200 with a reason, so reaching here means ATLAS was unreachable.
      setForecast({
        destination,
        isRealtimeData: false,
        resolvedDestination: null,
        latitude: null,
        longitude: null,
        localDate: null,
        forecastThrough: null,
        days: [],
        unavailableReason: 'Could not reach the ATLAS weather service.'
      });
    });

    return () => {
      active = false;
    };
  }, [destination]);

  return forecast;
}
