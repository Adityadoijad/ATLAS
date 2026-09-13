import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeftIcon,
  CloudIcon,
  DropletIcon,
  HeartIcon,
  MapPinIcon,
  SparklesIcon,
  StarIcon,
  UtensilsIcon,
  WindIcon } from
'lucide-react';
import { Badge, Button, Card, EmptyState, ErrorState, Skeleton } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';
import { findDestinationByName } from '../data/destinations';
import { fetchDestinationDetails } from '../services/atlasApi';
import { DestinationDetails, RealPlace } from '../types';
import { compactInr } from '../utils/format';

function PlaceList({
  title,
  icon,
  places,
  unavailableReason



}: {title: string;icon: React.ReactNode;places: RealPlace[];unavailableReason: string | null;}) {
  return (
    <Card className="p-5">
      <h2 className="flex items-center gap-2 text-[15px] font-bold text-ink">
        {icon}
        {title}
      </h2>
      {unavailableReason ?
      <p className="mt-3 text-[13px] text-muted">{unavailableReason}</p> :
      places.length === 0 ?
      <p className="mt-3 text-[13px] text-muted">No results found nearby.</p> :

      <ul className="mt-4 space-y-3">
          {places.map((place) =>
        <li key={`${place.name}-${place.latitude}`} className="flex items-start justify-between gap-3 border-b border-line pb-3 last:border-0 last:pb-0">
              <div>
                <p className="text-[13.5px] font-semibold text-ink">{place.name}</p>
                {place.category && <p className="text-[12px] text-muted">{place.category}</p>}
                {place.address && <p className="mt-0.5 text-[12px] text-muted">{place.address}</p>}
              </div>
              {place.rating != null &&
          <span className="inline-flex shrink-0 items-center gap-1 text-[12px] font-semibold text-ink">
                  <StarIcon className="h-3.5 w-3.5 fill-warning text-warning" />
                  {place.rating}
                </span>
          }
            </li>
        )}
        </ul>
      }
      <p className="mt-4 text-[11px] text-muted">
        {unavailableReason ? 'Source: unavailable' : places.length > 0 ? `Source: ${places[0].source}` : ''}
      </p>
    </Card>);

}

export function DestinationDetailsPage() {
  const { name } = useParams<{name: string;}>();
  const navigate = useNavigate();
  const { toggleSaved, isSaved } = useAtlas();
  const decodedName = decodeURIComponent(name ?? '');
  const catalogEntry = findDestinationByName(decodedName) ?? null;
  const displayName = catalogEntry?.name ?? decodedName;

  const [details, setDetails] = useState<DestinationDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    const token = localStorage.getItem('atlas_access_token');
    if (!token) {
      setError('Log in to see real-time destination information.');
      setLoading(false);
      return;
    }
    setLoading(true);
    setError('');
    fetchDestinationDetails(decodedName, token).
    then(setDetails).
    catch((reason) => setError(reason instanceof Error ? reason.message : 'Could not load destination information.')).
    finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decodedName]);

  const saved = catalogEntry ? isSaved(catalogEntry.id) : false;

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1.5 text-[13px] font-semibold text-muted hover:text-ink">

        <ArrowLeftIcon className="h-3.5 w-3.5" />
        Back
      </button>

      <Card className="overflow-hidden">
        {catalogEntry &&
        <div className="relative h-56">
            <img src={catalogEntry.image} alt={displayName} className="h-full w-full object-cover" />
            <div className="absolute inset-0 bg-slate-900/40" />
            <button
            type="button"
            onClick={() => toggleSaved(catalogEntry.id, catalogEntry.name)}
            aria-pressed={saved}
            className="absolute right-4 top-4 rounded-full bg-white/90 p-2.5 text-slate-600 shadow-sm backdrop-blur hover:text-danger">

              <HeartIcon className={saved ? 'h-4 w-4 fill-danger text-danger' : 'h-4 w-4'} />
            </button>
            <div className="absolute inset-x-0 bottom-0 p-6">
              <h1 className="font-display text-3xl font-bold text-white">{displayName}</h1>
              <p className="flex items-center gap-1 text-[13.5px] text-white/85">
                <MapPinIcon className="h-3.5 w-3.5" />
                {catalogEntry.country}
              </p>
            </div>
          </div>
        }
        <div className="p-6">
          {!catalogEntry &&
          <>
              <h1 className="font-display text-2xl font-bold text-ink">{displayName}</h1>
              <p className="mt-1 text-[13px] text-muted">Discovered destination — full details load from live data below.</p>
            </>
          }
          {catalogEntry &&
          <>
              <p className="mt-3 text-[14px] leading-relaxed text-muted">{catalogEntry.description}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {catalogEntry.categories.map((category) =>
              <Badge key={category} tone="accent">{category}</Badge>
              )}
              </div>
              <div className="mt-4 flex flex-wrap items-center gap-4 text-[13px] text-muted">
                <span className="inline-flex items-center gap-1">
                  <StarIcon className="h-3.5 w-3.5 fill-warning text-warning" />
                  {catalogEntry.rating} ({catalogEntry.reviews.toLocaleString()} reviews)
                </span>
                <span>{catalogEntry.durationDays} days · Best season {catalogEntry.bestSeason}</span>
                <span className="font-semibold text-brand">From {compactInr(catalogEntry.budgetFrom)}</span>
              </div>
            </>
          }
          <Button
            className="mt-5"
            icon={<SparklesIcon className="h-4 w-4" />}
            onClick={() => navigate('/plan', { state: { destination: displayName } })}>

            Plan a trip here
          </Button>
        </div>
      </Card>

      {loading &&
      <div className="grid gap-5 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) =>
        <Card key={i} className="p-5">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="mt-3 h-3 w-full" />
              <Skeleton className="mt-2 h-3 w-2/3" />
            </Card>
        )}
        </div>
      }

      {!loading && error &&
      <ErrorState message={error} onRetry={load} />
      }

      {!loading && !error && details &&
      <div className="grid gap-5 lg:grid-cols-3">
          <Card className="p-5">
            <h2 className="flex items-center gap-2 text-[15px] font-bold text-ink">
              <CloudIcon className="h-4 w-4 text-brand" />
              Weather
            </h2>
            {!details.weather.isRealtimeData ?
          <p className="mt-3 text-[13px] text-muted">{details.weather.unavailableReason ?? 'Weather data unavailable'}</p> :

          <>
                <p className="mt-3 text-3xl font-bold text-ink">{Math.round(details.weather.temperatureC ?? 0)}°C</p>
                <p className="text-[13px] capitalize text-muted">{details.weather.condition}</p>
                <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] text-muted">
                  <span>Feels like {Math.round(details.weather.feelsLikeC ?? 0)}°C</span>
                  <span className="inline-flex items-center gap-1"><DropletIcon className="h-3.5 w-3.5" />{details.weather.humidityPercent}% humidity</span>
                  <span className="inline-flex items-center gap-1"><WindIcon className="h-3.5 w-3.5" />{details.weather.windSpeedMs} m/s wind</span>
                </div>
                {details.weather.forecast.length > 0 &&
            <div className="mt-4 flex justify-between border-t border-line pt-3 text-[11px] text-muted">
                    {details.weather.forecast.map((day) =>
              <div key={day.timestamp} className="text-center">
                        <p>{new Date(day.timestamp).toLocaleDateString(undefined, { weekday: 'short' })}</p>
                        <p className="font-semibold text-ink">{Math.round(day.temperatureC)}°</p>
                      </div>
              )}
                  </div>
            }
              </>
          }
            <p className="mt-4 text-[11px] text-muted">{details.weather.isRealtimeData ? 'Source: OpenWeatherMap (live)' : 'Source: unavailable'}</p>
          </Card>

          <PlaceList
          title="Activities & Attractions"
          icon={<SparklesIcon className="h-4 w-4 text-brand" />}
          places={details.activities}
          unavailableReason={details.activitiesUnavailableReason} />


          <PlaceList
          title="Restaurants"
          icon={<UtensilsIcon className="h-4 w-4 text-brand" />}
          places={details.restaurants}
          unavailableReason={details.restaurantsUnavailableReason} />

        </div>
      }

      {!loading && !error && !details &&
      <EmptyState icon={<MapPinIcon className="h-5 w-5" />} title="No data available" description="Could not load information for this destination." />
      }
    </div>);

}
