import { ClockIcon, GlobeIcon, PhoneIcon, UtensilsIcon } from 'lucide-react';
import { Card } from '../ui/Primitives';

/**
 * Live eating places near the destination, from OpenStreetMap via the
 * planner's Food agent.
 *
 * Everything shown here comes from an OSM tag that actually exists — fields
 * the map has not been tagged with are omitted rather than rendered empty.
 * Note there are deliberately no prices: OSM publishes none, and the meal
 * budget shown elsewhere is an AI estimate, not live data.
 */
export interface FoodPlace {
  name: string;
  category?: string | null;
  cuisine?: string | null;
  address?: string | null;
  phone?: string | null;
  website?: string | null;
  opening_hours?: string | null;
}

const formatCategory = (category: string) => category.replace(/_/g, ' ');

export function FoodPlacesCard({ places, destination }: {places: FoodPlace[];destination: string;}) {
  if (places.length === 0) return null;

  return (
    <Card className="p-5">
      <h2 className="flex items-center gap-2 text-[15px] font-bold text-ink">
        <UtensilsIcon className="h-4 w-4 text-brand" />
        Where to eat in {destination}
      </h2>
      <p className="mt-1 text-[12px] text-muted">
        Live places from OpenStreetMap. Prices are not published by OSM — meal costs elsewhere are estimates.
      </p>

      <ul className="mt-4 space-y-3">
        {places.slice(0, 6).map((place) =>
        <li key={`${place.name}-${place.address ?? ''}`} className="border-b border-line pb-3 last:border-0 last:pb-0">
            <p className="text-[13.5px] font-semibold text-ink">{place.name}</p>
            {(place.category || place.cuisine) &&
          <p className="text-[12px] capitalize text-muted">
                {[place.category ? formatCategory(place.category) : null, place.cuisine].
            filter(Boolean).
            join(' · ')}
              </p>
          }
            {place.address && <p className="mt-0.5 text-[12px] text-muted">{place.address}</p>}
            {place.opening_hours &&
          <p className="mt-0.5 flex items-start gap-1 text-[12px] text-muted">
                <ClockIcon className="mt-[2px] h-3 w-3 shrink-0" />
                <span className="break-words">{place.opening_hours}</span>
              </p>
          }
            {(place.phone || place.website) &&
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px]">
                {place.phone &&
            <a href={`tel:${place.phone}`} className="inline-flex items-center gap-1 text-brand hover:underline">
                    <PhoneIcon className="h-3 w-3" />
                    {place.phone}
                  </a>
            }
                {place.website &&
            <a
              href={place.website}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1 text-brand hover:underline">

                    <GlobeIcon className="h-3 w-3" />
                    Website
                  </a>
            }
              </p>
          }
          </li>
        )}
      </ul>

      {/* OpenStreetMap data is ODbL-licensed; attribution must stay visible. */}
      <p className="mt-4 text-[11px] text-muted">
        Food place data ©{' '}
        <a
          href="https://www.openstreetmap.org/copyright"
          target="_blank"
          rel="noreferrer noopener"
          className="underline hover:text-ink">

          OpenStreetMap
        </a>{' '}
        contributors
      </p>
    </Card>);

}
