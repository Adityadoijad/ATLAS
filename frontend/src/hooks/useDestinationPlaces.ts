import { useEffect, useState } from 'react';
import { DestinationDetails } from '../types';
import { fetchDestinationDetails } from '../services/atlasApi';

/**
 * Real restaurants and attractions for a destination, via ATLAS's own API.
 *
 * Reuses `/api/destinations/:name/details`, which already aggregates
 * OpenStreetMap (restaurants) and OpenTripMap (attractions) and reports each
 * section's failure independently. Nothing new is introduced here.
 *
 * `undefined` means the request is still in flight. A finished-but-empty
 * result carries an `unavailableReason`, so the page can say why rather than
 * showing an unexplained blank — or, as it used to, a static demo catalogue
 * presented as live listings.
 */
export function useDestinationPlaces(destination: string | null): {
  details: DestinationDetails | undefined;
  error: string | null;
} {
  const [details, setDetails] = useState<DestinationDetails | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!destination?.trim()) {
      setDetails(undefined);
      setError(null);
      return;
    }

    const token = localStorage.getItem('atlas_access_token');
    if (!token) {
      setDetails(undefined);
      setError('Sign in to look up real places for a destination.');
      return;
    }

    let active = true;
    setDetails(undefined);
    setError(null);

    fetchDestinationDetails(destination.trim(), token).
    then((data) => {
      if (active) setDetails(data);
    }).
    catch(() => {
      if (active) setError('Could not reach the ATLAS places service. Please try again shortly.');
    });

    return () => {
      active = false;
    };
  }, [destination]);

  return { details, error };
}
