import { useEffect, useMemo, useState } from 'react';
import { SearchIcon, UtensilsIcon } from 'lucide-react';
import { RealPlaceCard } from '../components/cards/RealPlaceCard';
import { Button, Card, EmptyState, Field, Input, Pill, Skeleton } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';
import { useDestinationPlaces } from '../hooks/useDestinationPlaces';
import { relevantTripForWeather } from '../utils/weatherOutlook';

/**
 * Real restaurants near a destination, from OpenStreetMap.
 *
 * This page previously rendered a fixed eight-entry catalogue — complete with
 * ratings, prices and "2.4 km away" distances that came from a source file —
 * as though it were live listings. It now asks the same backend the itinerary's
 * food card uses, and when that has nothing to say, the page says so.
 */
export function FoodPage() {
  const { trips } = useAtlas();
  // Defaults to the trip the traveller is actually taking, the way the weather
  // card does, so the page is useful without typing anything.
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
  const [cuisine, setCuisine] = useState('all');

  const { details, error } = useDestinationPlaces(destination || null);
  const restaurants = useMemo(() => details?.restaurants ?? [], [details]);

  // Built from what came back, not from a fixed list — a destination with no
  // Japanese food should not offer a "Japanese" filter.
  const cuisines = useMemo(() => {
    const found = new Set<string>();
    for (const place of restaurants) {
      if (place.cuisine) found.add(place.cuisine);
    }
    return ['all', ...Array.from(found).sort()];
  }, [restaurants]);

  const results = restaurants.filter((r) => cuisine === 'all' || r.cuisine === cuisine);
  const loading = Boolean(destination) && details === undefined && !error;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold text-ink">Food & Restaurants</h1>
        <p className="mt-1.5 text-[15px] text-muted">
          Real places from OpenStreetMap. Prices and ratings are shown only where the
          source publishes them.
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
            <Field label="Destination" htmlFor="food-destination">
            <Input
              id="food-destination"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. Udaipur" />

            </Field>
          </div>
          <Button type="submit" icon={<SearchIcon className="h-4 w-4" />}>
            Find restaurants
          </Button>
        </form>
      </Card>

      {!destination &&
      <EmptyState
        icon={<UtensilsIcon className="h-5 w-5" />}
        title="Choose a destination"
        description="Enter a place and ATLAS will look up restaurants that actually exist there." />

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
        icon={<UtensilsIcon className="h-5 w-5" />}
        title="Restaurants unavailable"
        description={error} />

      }

      {details && !error &&
      <>
          {cuisines.length > 1 &&
        <div className="no-scrollbar -mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
              {cuisines.map((c) =>
          <Pill key={c} active={c === cuisine} onClick={() => setCuisine(c)}>
                  {c === 'all' ? 'All cuisines' : c}
                </Pill>
          )}
            </div>
        }

          {results.length === 0 ?
        <EmptyState
          icon={<UtensilsIcon className="h-5 w-5" />}
          title="No restaurants found"
          description={
          details.restaurantsUnavailableReason ??
          `OpenStreetMap lists no restaurants matching this filter in ${details.destination}.`
          } /> :


        <>
              <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {results.map((place) =>
            <RealPlaceCard key={`${place.name}-${place.latitude}-${place.longitude}`} place={place} />
            )}
              </div>
              <p className="text-[11.5px] text-muted">
                {results.length} place{results.length === 1 ? '' : 's'} in {details.destination} ·
                Data © OpenStreetMap contributors (ODbL)
              </p>
            </>
        }
        </>
      }
    </div>);

}
