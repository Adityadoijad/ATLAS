import { ExternalLinkIcon, MapPinIcon, PhoneIcon, StarIcon, UtensilsIcon } from 'lucide-react';
import { RealPlace } from '../../types';
import { Card } from '../ui/Primitives';

/**
 * One real place, from OpenStreetMap or OpenTripMap.
 *
 * Every field here is optional in the source data, and an absent field is
 * rendered as absent — not as a zero, a dash, or a plausible-looking default.
 * The static catalogue this replaced gave every listing a rating between 4.4
 * and 4.9, a price and a distance, none of which came from anywhere.
 *
 * A rating shows only when the provider actually published one. OpenStreetMap
 * does not carry ratings at all, so most food places legitimately have none.
 */
export function RealPlaceCard({ place }: {place: RealPlace;}) {
  const detail = [place.cuisine, place.category?.replace(/_/g, ' ')].
  filter(Boolean).
  join(' · ');

  return (
    <Card className="flex flex-col p-4">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-[14.5px] font-semibold text-ink">{place.name}</h3>
        {place.rating !== null &&
        <span className="inline-flex shrink-0 items-center gap-1 text-[12.5px] text-muted">
            <StarIcon className="h-3.5 w-3.5 fill-warning text-warning" />
            {place.rating.toFixed(1)}
          </span>
        }
      </div>

      {detail &&
      <p className="mt-1 inline-flex items-center gap-1.5 text-[12.5px] capitalize text-muted">
          <UtensilsIcon className="h-3.5 w-3.5" /> {detail}
        </p>
      }

      {place.address &&
      <p className="mt-2 inline-flex items-start gap-1.5 text-[12.5px] text-muted">
          <MapPinIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {place.address}
        </p>
      }

      {place.openingHours &&
      <p className="mt-1.5 text-[12px] text-muted">Hours: {place.openingHours}</p>
      }

      <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1.5 pt-3 text-[12px]">
        {place.phone &&
        <a href={`tel:${place.phone}`} className="inline-flex items-center gap-1 text-brand hover:underline">
            <PhoneIcon className="h-3.5 w-3.5" /> {place.phone}
          </a>
        }
        {place.website &&
        <a
          href={place.website}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-brand hover:underline">

            Website <ExternalLinkIcon className="h-3 w-3" />
          </a>
        }
        <span className="ml-auto text-[11px] capitalize text-muted/80">{place.source.replace(/_/g, ' ')}</span>
      </div>
    </Card>);

}
