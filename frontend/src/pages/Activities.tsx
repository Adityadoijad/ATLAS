import { useState } from 'react';
import { TicketIcon } from 'lucide-react';
import { ActivityCard } from '../components/cards/ContentCards';
import { EmptyState, Pill } from '../components/ui/Primitives';
import { Dropdown } from '../components/ui/Overlays';
import { activities } from '../data/catalog';

const categories = ['All', 'Attractions', 'Experiences', 'Adventure', 'Culture', 'Nature', 'Hidden Gems'];

export function ActivitiesPage() {
  const [category, setCategory] = useState('All');
  const [sort, setSort] = useState('recommended');

  let results = activities.filter((a) => category === 'All' || a.category === category);
  if (sort === 'rating') results = [...results].sort((a, b) => b.rating - a.rating);
  if (sort === 'price') results = [...results].sort((a, b) => a.price - b.price);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink">Activities & Experiences</h1>
          <p className="mt-1.5 text-[15px] text-muted">
            Every option carries the Activity Agent's reason for recommending it.
          </p>
        </div>
        <Dropdown
          label="Sort:"
          align="right"
          value={sort}
          onChange={setSort}
          options={[
          { value: 'recommended', label: 'Recommended' },
          { value: 'rating', label: 'Top rated' },
          { value: 'price', label: 'Lowest price' }]
          } />
        
      </header>

      <div className="no-scrollbar -mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
        {categories.map((c) =>
        <Pill key={c} active={c === category} onClick={() => setCategory(c)}>
            {c}
          </Pill>
        )}
      </div>

      {results.length === 0 ?
      <EmptyState
        icon={<TicketIcon className="h-5 w-5" />}
        title="No activities in this category"
        description="Try another category — hidden gems and experiences usually have availability." /> :


      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {results.map((a) =>
        <ActivityCard key={a.id} activity={a} />
        )}
        </div>
      }
    </div>);

}
