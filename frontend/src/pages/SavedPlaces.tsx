import { useState } from 'react';
import { BookmarkIcon } from 'lucide-react';
import { SavedPlaceCard } from '../components/cards/ContentCards';
import { EmptyState, Tabs } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';

const tabs = ['Destinations', 'Hotels', 'Restaurants', 'Activities'] as const;

export function SavedPlacesPage() {
  const { savedItems, removeSavedItem } = useAtlas();
  const [tab, setTab] = useState<string>('Destinations');

  const results = savedItems.filter((p) => p.kind === tab);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-3xl font-bold text-ink">Saved Places</h1>
        <p className="mt-1.5 text-[15px] text-muted">Everything you have bookmarked, ready to drop into a trip.</p>
      </header>

      <Tabs
        value={tab}
        onChange={setTab}
        tabs={tabs.map((t) => ({ id: t, label: t, count: savedItems.filter((p) => p.kind === t).length }))} />
      

      {results.length === 0 ?
      <EmptyState
        icon={<BookmarkIcon className="h-5 w-5" />}
        title={`No saved ${tab.toLowerCase()} yet`}
        description="Tap the heart icon on any card to keep it here for later." /> :


      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {results.map((place) =>
        <SavedPlaceCard key={place.id} place={place} onRemove={() => removeSavedItem(place.id)} />
        )}
        </div>
      }
    </div>);

}
