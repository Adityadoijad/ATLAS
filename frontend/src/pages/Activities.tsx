import { useEffect, useState } from 'react';
import { SearchIcon, TicketIcon } from 'lucide-react';
import { RealPlaceCard } from '../components/cards/RealPlaceCard';
import { Button, Card, EmptyState, Field, Input, Skeleton } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';
import { useDestinationPlaces } from '../hooks/useDestinationPlaces';
import { relevantTripForWeather } from '../utils/weatherOutlook';

/**
 * Real attractions near a destination, from OpenTripMap.
 *
 * Replaces a fixed catalogue whose every entry carried an invented rating
 * (4.4–4.9), price and review count. Those fields are shown here only when the
 * provider publishes them, which for most attractions means not at all.
 */
export function ActivitiesPage() {
  const { trips } = useAtlas();
  const suggested = relevantTripForWeather(trips)?.destination ?? '';
  const [input, setInput] = useState(suggested);
  const [destination, setDestination] = useState(suggested);

  // Trips arrive from the API after first render, so the suggestion is empty
  // when this state initialises. Adopt it once, and only while the field is
  // still untouched — a traveller who has typed something keeps it.
  useEffect(() => {
    if (!suggested) return;
    setInput((current) => current || suggested);
    setDestination((current) => current || suggested);
  }, [suggested]);

  const { details, error } = useDestinationPlaces(destination || null);
  const activities = details?.activities ?? [];
  const loading = Boolean(destination) && details === undefined && !error;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold text-ink">Activities & Experiences</h1>
        <p className="mt-1.5 text-[15px] text-muted">
          Real attractions from OpenTripMap. Nothing is listed that the source does not
          actually carry.
        </p>
      </header>

      <Card className="p-5">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            setDestination(input.trim());
          }}>

          <div className="min-w-[220px] flex-1">
            <Field label="Destination" htmlFor="activities-destination">
            <Input
              id="activities-destination"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. Udaipur" />

            </Field>
          </div>
          <Button type="submit" icon={<SearchIcon className="h-4 w-4" />}>
            Find activities
          </Button>
        </form>
      </Card>

      {!destination &&
      <EmptyState
        icon={<TicketIcon className="h-5 w-5" />}
        title="Choose a destination"
        description="Enter a place and ATLAS will look up attractions that actually exist there." />

      }

      {loading &&
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((slot) =>
        <Skeleton key={slot} className="h-40" />
        )}
        </div>
      }

      {error &&
      <EmptyState
        icon={<TicketIcon className="h-5 w-5" />}
        title="Activities unavailable"
        description={error} />

      }

      {details && !error && (
      activities.length === 0 ?
      <EmptyState
        icon={<TicketIcon className="h-5 w-5" />}
        title="No activities found"
        description={
        details.activitiesUnavailableReason ??
        `No attractions were found for ${details.destination}.`
        } /> :


      <>
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {activities.map((place) =>
          <RealPlaceCard key={`${place.name}-${place.latitude}-${place.longitude}`} place={place} />
          )}
            </div>
            <p className="text-[11.5px] text-muted">
              {activities.length} place{activities.length === 1 ? '' : 's'} in {details.destination}
            </p>
          </>)

      }
    </div>);

}
