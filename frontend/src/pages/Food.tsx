import { useMemo, useState } from 'react';
import { UtensilsIcon } from 'lucide-react';
import { CommunityInsight, RestaurantCard } from '../components/cards/ContentCards';
import { Button, Card, EmptyState, Field, Pill } from '../components/ui/Primitives';
import { Dropdown } from '../components/ui/Overlays';
import { restaurants } from '../data/catalog';
import { compactInr } from '../utils/format';

const tagFilters = ['All', 'Vegetarian', 'Local food', 'Street food', 'Fine dining', 'Non-vegetarian', 'Budget-friendly'];

export function FoodPage() {
  const [tag, setTag] = useState('All');
  const [cuisine, setCuisine] = useState('all');
  const [maxPrice, setMaxPrice] = useState(3000);
  const [minRating, setMinRating] = useState(4);
  const [maxDistance, setMaxDistance] = useState(15);

  const cuisines = useMemo(
    () => ['all', ...Array.from(new Set(restaurants.map((r) => r.cuisine)))],
    []
  );

  const results = restaurants.filter(
    (r) =>
    (tag === 'All' || r.tags.includes(tag)) && (
    cuisine === 'all' || r.cuisine === cuisine) &&
    r.pricePerPerson <= maxPrice &&
    r.rating >= minRating &&
    r.distanceKm <= maxDistance
  );

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold text-ink">Food & Restaurants</h1>
        <p className="mt-1.5 text-[15px] text-muted">
          Ranked by the Food Agent using traveller reviews, distance and your dietary preferences.
        </p>
      </header>

      <div className="no-scrollbar -mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
        {tagFilters.map((t) =>
        <Pill key={t} active={t === tag} onClick={() => setTag(t)}>
            {t}
          </Pill>
        )}
      </div>

      <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
        <Card className="h-fit space-y-5 p-5">
          <p className="text-[13px] font-bold text-ink">Filters</p>
          <Dropdown
            label="Cuisine:"
            value={cuisine}
            onChange={setCuisine}
            options={cuisines.map((c) => ({ value: c, label: c === 'all' ? 'All cuisines' : c }))} />
          
          <Field label={`Budget per person · ${compactInr(maxPrice)}`}>
            <input
              type="range"
              min={300}
              max={3000}
              step={100}
              value={maxPrice}
              onChange={(e) => setMaxPrice(Number(e.target.value))}
              className="w-full accent-[#2563EB]"
              aria-label="Maximum price per person" />
            
          </Field>
          <Field label={`Minimum rating · ${minRating.toFixed(1)}`}>
            <input
              type="range"
              min={3}
              max={5}
              step={0.1}
              value={minRating}
              onChange={(e) => setMinRating(Number(e.target.value))}
              className="w-full accent-[#2563EB]"
              aria-label="Minimum rating" />
            
          </Field>
          <Field label={`Distance · under ${maxDistance} km`}>
            <input
              type="range"
              min={1}
              max={15}
              step={1}
              value={maxDistance}
              onChange={(e) => setMaxDistance(Number(e.target.value))}
              className="w-full accent-[#2563EB]"
              aria-label="Maximum distance" />
            
          </Field>
          <Button
            variant="secondary"
            className="w-full"
            onClick={() => {
              setTag('All');
              setCuisine('all');
              setMaxPrice(3000);
              setMinRating(4);
              setMaxDistance(15);
            }}>
            
            Reset filters
          </Button>
        </Card>

        <div className="space-y-6">
          {results.length === 0 ?
          <EmptyState
            icon={<UtensilsIcon className="h-5 w-5" />}
            title="No restaurants match these filters"
            description="Widen the budget or distance range to see more options nearby." /> :


          <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {results.map((r) =>
            <RestaurantCard key={r.id} restaurant={r} />
            )}
            </div>
          }

          <CommunityInsight
            title="Community insight · local food scene"
            quote="Travellers frequently mention this area for authentic local food, and recommend eating before 8pm to avoid long waits."
            rating={4.7}
            reviews={12840}
            positives={['Authentic regional cooking', 'Good vegetarian coverage', 'Fair pricing outside tourist strips']}
            concerns={['Long waits at peak hours', 'Limited card payments at smaller places']} />
          
        </div>
      </div>
    </div>);

}
