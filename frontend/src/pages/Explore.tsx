import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CompassIcon, SearchIcon, SlidersHorizontalIcon } from 'lucide-react';
import { DestinationCard } from '../components/cards/DestinationCard';
import { Button, Card, EmptyState, Field, Input, Pill, Skeleton } from '../components/ui/Primitives';
import { Drawer, Dropdown } from '../components/ui/Overlays';
import { categoryPills } from '../data/destinations';
import { fetchDestinations } from '../services/atlasApi';
import { Destination } from '../types';
import { compactInr } from '../utils/format';

export function ExplorePage() {
  const [params, setParams] = useSearchParams();
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('All');
  const [sort, setSort] = useState('recommended');
  const [maxBudget, setMaxBudget] = useState(200000);
  const [minRating, setMinRating] = useState(0);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const query = params.get('q') ?? '';

  useEffect(() => {
    let active = true;
    fetchDestinations().then((data) => {
      if (active) {
        setDestinations(data);
        setLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const results = useMemo(() => {
    let list = destinations.filter((d) => {
      const matchesQuery =
      !query ||
      `${d.name} ${d.country} ${d.description}`.toLowerCase().includes(query.toLowerCase());
      const matchesCategory = category === 'All' || d.categories.includes(category as Destination['categories'][number]);
      return matchesQuery && matchesCategory && d.budgetFrom <= maxBudget && d.rating >= minRating;
    });
    if (sort === 'rating') list = [...list].sort((a, b) => b.rating - a.rating);
    if (sort === 'budget-low') list = [...list].sort((a, b) => a.budgetFrom - b.budgetFrom);
    if (sort === 'budget-high') list = [...list].sort((a, b) => b.budgetFrom - a.budgetFrom);
    return list;
  }, [destinations, query, category, sort, maxBudget, minRating]);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold text-ink">Explore Destinations</h1>
        <p className="mt-1.5 text-[15px] text-muted">Discover amazing places around the world.</p>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-muted" />
          <Input
            value={query}
            onChange={(e) => setParams(e.target.value ? { q: e.target.value } : {})}
            placeholder="Search destinations, countries, experiences..."
            aria-label="Search destinations"
            className="h-12 pl-12" />
          
        </div>
        <Button variant="secondary" className="h-12" icon={<SlidersHorizontalIcon className="h-4 w-4" />} onClick={() => setFiltersOpen(true)}>
          Filters
        </Button>
        <div className="hidden sm:block">
          <Dropdown
            label="Sort:"
            align="right"
            value={sort}
            onChange={setSort}
            options={[
            { value: 'recommended', label: 'Recommended' },
            { value: 'rating', label: 'Top rated' },
            { value: 'budget-low', label: 'Budget: low to high' },
            { value: 'budget-high', label: 'Budget: high to low' }]
            } />
          
        </div>
      </div>

      <div className="no-scrollbar -mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
        {categoryPills.map((pill) =>
        <Pill key={pill} active={pill === category} onClick={() => setCategory(pill)}>
            {pill}
          </Pill>
        )}
      </div>

      <p className="text-[13px] text-muted">
        {loading ? 'Searching destinations…' : `${results.length} destination${results.length === 1 ? '' : 's'} found`}
      </p>

      {loading ?
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) =>
        <Card key={i} className="overflow-hidden p-0">
              <Skeleton className="h-44 rounded-none" />
              <div className="space-y-2 p-4">
                <Skeleton className="h-4 w-2/3" />
                <Skeleton className="h-3 w-1/3" />
                <Skeleton className="h-3 w-full" />
              </div>
            </Card>
        )}
        </div> :
      results.length === 0 ?
      <EmptyState
        icon={<CompassIcon className="h-5 w-5" />}
        title="No destinations match those filters"
        description="Try widening your budget, lowering the rating threshold or clearing the category."
        action={
        <Button
          variant="secondary"
          onClick={() => {
            setCategory('All');
            setMaxBudget(200000);
            setMinRating(0);
            setParams({});
          }}>
          
              Reset filters
            </Button>
        } /> :


      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {results.map((destination) =>
        <DestinationCard key={destination.id} destination={destination} variant="detailed" />
        )}
        </div>
      }

      <Drawer open={filtersOpen} onClose={() => setFiltersOpen(false)} title="Filters">
        <div className="space-y-6">
          <Field label={`Maximum budget · ${compactInr(maxBudget)}`}>
            <input
              type="range"
              min={15000}
              max={200000}
              step={5000}
              value={maxBudget}
              onChange={(e) => setMaxBudget(Number(e.target.value))}
              className="w-full accent-[#2563EB]"
              aria-label="Maximum budget" />
            
          </Field>
          <Field label={`Minimum rating · ${minRating.toFixed(1)}`}>
            <input
              type="range"
              min={0}
              max={5}
              step={0.1}
              value={minRating}
              onChange={(e) => setMinRating(Number(e.target.value))}
              className="w-full accent-[#2563EB]"
              aria-label="Minimum rating" />
            
          </Field>
          <Field label="Category">
            <div className="flex flex-wrap gap-2">
              {categoryPills.map((pill) =>
              <Pill key={pill} active={pill === category} onClick={() => setCategory(pill)}>
                  {pill}
                </Pill>
              )}
            </div>
          </Field>
          <div className="flex gap-3 pt-2">
            <Button className="flex-1" onClick={() => setFiltersOpen(false)}>
              Show {results.length} results
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setMaxBudget(200000);
                setMinRating(0);
                setCategory('All');
              }}>
              
              Reset
            </Button>
          </div>
        </div>
      </Drawer>
    </div>);

}
