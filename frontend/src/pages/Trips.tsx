import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LuggageIcon, PlusIcon } from 'lucide-react';
import { TripCard } from '../components/cards/ContentCards';
import { Button, EmptyState, Tabs } from '../components/ui/Primitives';
import { Modal } from '../components/ui/Overlays';
import { useAtlas } from '../contexts/AtlasContext';
import { Trip } from '../types';

export function TripsPage() {
  const { trips, removeTrip } = useAtlas();
  const [tab, setTab] = useState('upcoming');
  const [pendingDelete, setPendingDelete] = useState<Trip | null>(null);
  const navigate = useNavigate();

  const filtered = trips.filter((t) => t.status === tab);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink">My Trips</h1>
          <p className="mt-1.5 text-[15px] text-muted">Upcoming journeys, past trips and saved plans.</p>
        </div>
        <Button icon={<PlusIcon className="h-4 w-4" />} onClick={() => navigate('/plan')}>
          Plan a New Trip
        </Button>
      </header>

      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
        { id: 'upcoming', label: 'Upcoming', count: trips.filter((t) => t.status === 'upcoming').length },
        { id: 'past', label: 'Past trips', count: trips.filter((t) => t.status === 'past').length },
        { id: 'saved', label: 'Saved plans', count: trips.filter((t) => t.status === 'saved').length }]
        } />
      

      {filtered.length === 0 ?
      <EmptyState
        icon={<LuggageIcon className="h-5 w-5" />}
        title="Nothing here yet"
        description="When you generate or save an itinerary it will appear in this list."
        action={<Button onClick={() => navigate('/plan')}>Plan a New Trip</Button>} /> :


      <div className="space-y-4">
          {filtered.map((trip) =>
        <TripCard key={trip.id} trip={trip} onView={() => navigate('/itinerary')} onDelete={() => setPendingDelete(trip)} />
        )}
        </div>
      }

      <Modal
        open={Boolean(pendingDelete)}
        onClose={() => setPendingDelete(null)}
        title="Delete this trip?"
        description="The itinerary and all its saved days will be removed."
        footer={
        <>
            <Button variant="ghost" onClick={() => setPendingDelete(null)}>
              Keep trip
            </Button>
            <Button
            variant="danger"
            onClick={() => {
              if (pendingDelete) removeTrip(pendingDelete.id);
              setPendingDelete(null);
            }}>
            
              Delete trip
            </Button>
          </>
        }>
        
        <p className="text-[14px] text-muted">
          {pendingDelete?.destination} · This cannot be undone in the prototype.
        </p>
      </Modal>
    </div>);

}
