import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CompassIcon, SearchIcon } from 'lucide-react';
import { DiscoverIndiaCard } from '../components/home/DiscoverIndiaCard';
import { DiscoverMore } from '../components/discover/DiscoverMore';
import { Card, EmptyState, Input, Pill, SectionHeading, Skeleton } from '../components/ui/Primitives';
import { fetchIndiaRecommendations } from '../services/atlasApi';
import { DiscoverIndiaRecommendation } from '../types';

/**
 * Destinations to explore, from the AI-curated India recommendations endpoint.
 *
 * This page used to call `fetchDestinations()`, which waited 320ms and then
 * returned a twelve-entry array from a source file — a loading spinner over a
 * hardcoded list. It now calls `GET /api/destinations/recommendations`, the
 * same Groq-generated, Nominatim-validated, Wikimedia-illustrated data the
 * home page uses.
 *
 * The rating and budget filters are gone with it. They sorted on `rating` and
 * `budgetFrom` fields that existed only in that source file; the live data
 * carries no such numbers, and inventing them to keep the controls would
 * reintroduce exactly what was removed. Search and tags filter on real fields.
 */
export function ExplorePage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [destinations, setDestinations] = useState<DiscoverIndiaRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [tag, setTag] = useState('All');
  const query = params.get('q') ?? '';

  useEffect(() => {
    let active = true;
    fetchIndiaRecommendations().
    then((data) => {
      if (!active) return;
      setDestinations(data);
      // The client swallows errors and returns [], so an empty list is the
      // only signal that something went wrong.
      setFailed(data.length === 0);
      setLoading(false);
    }).
    catch(() => {
      if (!active) return;
      setFailed(true);
      setLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  // Built from what actually came back rather than a fixed pill list.
  const tags = useMemo(() => {
    const found = new Set<string>();
    for (const destination of destinations) {
      for (const t of destination.tags) found.add(t);
    }
    return ['All', ...Array.from(found).sort()];
  }, [destinations]);

  const results = useMemo(
    () =>
    destinations.filter((d) => {
      const haystack = `${d.name} ${d.state} ${d.country} ${d.description} ${d.reason}`.toLowerCase();
      const matchesQuery = !query || haystack.includes(query.toLowerCase());
      const matchesTag = tag === 'All' || d.tags.includes(tag);
      return matchesQuery && matchesTag;
    }),
    [destinations, query, tag]
  );

  const usingFallback = results.some((d) => d.is_fallback);

  return (
    <div className="space-y-6">
      <SectionHeading
        title="Explore destinations"
        subtitle={
        usingFallback ?
        'Curated picks — live AI recommendations are unavailable right now.' :
        'AI-curated places across India, refreshed regularly.'
        } />


      <Card className="p-5">
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <Input
            aria-label="Search destinations"
            value={query}
            onChange={(e) => {
              const next = e.target.value;
              setParams(next ? { q: next } : {}, { replace: true });
            }}
            placeholder="Search by name, state or what it is known for..."
            className="pl-9" />

        </div>

        {tags.length > 1 &&
        <div className="no-scrollbar -mx-1 mt-4 flex gap-2 overflow-x-auto px-1 pb-1">
            {tags.map((t) =>
          <Pill key={t} active={t === tag} onClick={() => setTag(t)}>
                {t}
              </Pill>
          )}
          </div>
        }
      </Card>

      {loading &&
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((slot) =>
        <Card key={slot} className="overflow-hidden p-0">
              <Skeleton className="h-44 rounded-none" />
              <div className="space-y-2 p-4">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-3 w-1/3" />
                <Skeleton className="h-3 w-full" />
              </div>
            </Card>
        )}
        </div>
      }

      {!loading && failed &&
      <EmptyState
        icon={<CompassIcon className="h-5 w-5" />}
        title="Recommendations unavailable"
        description="ATLAS could not reach the recommendation service. Please try again shortly." />

      }

      {!loading && !failed && results.length === 0 &&
      <EmptyState
        icon={<CompassIcon className="h-5 w-5" />}
        title="No destinations match"
        description="Try a different search term or clear the filters." />

      }

      {!loading && results.length > 0 &&
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {results.map((destination) =>
        <DiscoverIndiaCard
          key={destination.full_name}
          destination={destination}
          onClick={() => navigate(`/explore/${encodeURIComponent(destination.name)}`)} />

        )}
        </div>
      }

      <DiscoverMore token={localStorage.getItem('atlas_access_token')} />
    </div>);

}
