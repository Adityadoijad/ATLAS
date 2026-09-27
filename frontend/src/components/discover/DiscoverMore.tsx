import { useState } from 'react';
import { CalendarRangeIcon, ImageOffIcon, MapPinIcon, RefreshCwIcon, SparklesIcon } from 'lucide-react';
import { Badge, Button, Card, ErrorState } from '../ui/Primitives';
import { discoverDestinations } from '../../services/atlasApi';
import { DiscoveredDestination } from '../../types';
import { compactInr } from '../../utils/format';

function DiscoveryCard({ destination }: {destination: DiscoveredDestination;}) {
  // A remote photo can still 404 or be blocked after we resolved it, so drop
  // back to the placeholder on load failure rather than showing a broken image.
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = Boolean(destination.imageUrl) && !imageFailed;

  return (
    <Card className="overflow-hidden">
      {showImage ?
      <img
        src={destination.imageUrl}
        alt={`${destination.name}, ${destination.country}`}
        onError={() => setImageFailed(true)}
        className="h-40 w-full object-cover" /> :

      <div
        className="flex h-40 w-full items-center justify-center bg-gradient-to-br from-brand/15 to-accent/15"
        aria-hidden="true">
          <ImageOffIcon className="h-6 w-6 text-muted" />
        </div>
      }

      <div className="p-4">
        <div className="flex flex-wrap gap-1.5">
          {destination.categories.map((category) =>
          <Badge key={category} tone="accent">{category}</Badge>
          )}
        </div>
        <h3 className="mt-2.5 text-[15px] font-bold text-ink">{destination.name}</h3>
        <p className="mt-0.5 flex items-center gap-1 text-[13px] text-muted">
          <MapPinIcon className="h-3.5 w-3.5" />
          {destination.country}
        </p>
        <p className="mt-2 text-[13px] leading-relaxed text-muted">{destination.description}</p>
        <div className="mt-3 flex items-center justify-between border-t border-line pt-3 text-[12px]">
          <span className="inline-flex items-center gap-1.5 text-muted">
            <CalendarRangeIcon className="h-3.5 w-3.5" />
            {destination.durationDays} Days · {destination.bestSeason}
          </span>
          <span className="font-semibold text-brand">From {compactInr(destination.budgetFrom)}</span>
        </div>
      </div>
    </Card>);

}

export function DiscoverMore({ token }: {token: string | null;}) {
  const [state, setState] = useState<'idle' | 'loading' | 'error' | 'done'>('idle');
  const [destinations, setDestinations] = useState<DiscoveredDestination[]>([]);
  const [error, setError] = useState('');

  const run = async () => {
    if (!token) return;
    setState('loading');
    setError('');
    try {
      const data = await discoverDestinations(token);
      setDestinations(data);
      setState('done');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not generate new suggestions.');
      setState('error');
    }
  };

  if (!token) return null;

  return (
    <div className="mt-5">
      {state === 'idle' &&
      <Button variant="outline" icon={<SparklesIcon className="h-4 w-4" />} onClick={run}>
          Discover something new
        </Button>
      }

      {state === 'loading' &&
      <Button variant="outline" loading disabled>
          Asking ATLAS for fresh ideas…
        </Button>
      }

      {state === 'error' &&
      <ErrorState message={error} onRetry={run} />
      }

      {state === 'done' &&
      <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {destinations.map((destination) =>
          <DiscoveryCard key={`${destination.name}-${destination.country}`} destination={destination} />
          )}
          </div>
          <Button variant="outline" size="sm" icon={<RefreshCwIcon className="h-3.5 w-3.5" />} onClick={run}>
            Discover more
          </Button>
        </div>
      }
    </div>);

}
