import { useEffect, useState } from 'react';
import { MapPinIcon } from 'lucide-react';
import { fetchDestinationPhoto } from '../../services/atlasApi';
import { cn } from '../../utils/format';

/**
 * A photograph of a specific place, or an honest absence of one.
 *
 * This exists because the alternative was worse than nothing: every
 * destination without a catalog entry used to fall back to `IMAGES.goa`, so a
 * Manali trip rendered a Goa beach under a Manali heading. A picture of the
 * wrong place is a factual claim, and it was wrong on most trips.
 *
 * `src` is used when the caller already holds a genuine photo for this place.
 * Otherwise the real one is fetched from Wikimedia via ATLAS's own endpoint,
 * and if there is none, a neutral panel names the destination in text. The
 * panel is deliberately not a photograph: nothing about it suggests it depicts
 * the place.
 */

// Resolved photos are shared process-wide. The same destination appears on the
// dashboard, the trips list and the itinerary header, and each should cost one
// lookup at most — the backend caches for a day, this avoids the round trip.
const photoCache = new Map<string, string | null>();

export function DestinationImage({
  destination,
  src,
  alt,
  className
}: {
  destination: string;
  /** A photo the caller already has. Empty or absent triggers a lookup. */
  src?: string;
  alt?: string;
  className?: string;
}) {
  const key = destination.trim().toLowerCase();
  const [resolved, setResolved] = useState<string | null | undefined>(() =>
  src ? src : photoCache.get(key)
  );

  useEffect(() => {
    if (src) {
      setResolved(src);
      return;
    }
    if (!destination.trim()) {
      setResolved(null);
      return;
    }
    if (photoCache.has(key)) {
      setResolved(photoCache.get(key));
      return;
    }

    let active = true;
    setResolved(undefined);
    fetchDestinationPhoto(destination).
    then((url) => {
      photoCache.set(key, url);
      if (active) setResolved(url);
    }).
    catch(() => {
      // A failed lookup is not a licence to show a different place. Cache the
      // absence so a broken network does not retry on every render.
      photoCache.set(key, null);
      if (active) setResolved(null);
    });

    return () => {
      active = false;
    };
  }, [destination, key, src]);

  if (resolved === undefined) {
    return <div className={cn('animate-pulse bg-subtle', className)} aria-hidden />;
  }

  if (resolved) {
    return (
      <img
        src={resolved}
        alt={alt ?? destination}
        className={cn('object-cover', className)}
        onError={() => {
          // The URL resolved but the image will not load. Fall back to the
          // placeholder, never to another destination's picture.
          photoCache.set(key, null);
          setResolved(null);
        }} />);


  }

  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-1.5 bg-gradient-to-br from-brand/10 to-accent/10',
        className
      )}
      role="img"
      aria-label={`No photograph available for ${destination}`}>

      <MapPinIcon className="h-5 w-5 text-brand/70" />
      <span className="px-3 text-center text-[12px] font-semibold text-muted">{destination}</span>
      <span className="text-[10.5px] text-muted/80">No photo available</span>
    </div>);

}
