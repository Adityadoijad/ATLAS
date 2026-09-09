import { useState } from 'react';
import { CalendarCheckIcon, PlusIcon } from 'lucide-react';
import { BookingCard } from '../components/cards/ContentCards';
import { BookingFlow } from '../components/booking/BookingFlow';
import { Badge, Button, Card, EmptyState, Tabs } from '../components/ui/Primitives';
import { Modal } from '../components/ui/Overlays';
import { useAtlas } from '../contexts/AtlasContext';
import { Booking } from '../types';
import { IMAGES } from '../data/destinations';
import { formatDate, inr } from '../utils/format';

export function BookingsPage() {
  const { bookings, cancelBooking } = useAtlas();
  const [tab, setTab] = useState('all');
  const [details, setDetails] = useState<Booking | null>(null);
  const [cancelTarget, setCancelTarget] = useState<Booking | null>(null);
  const [newBooking, setNewBooking] = useState(false);

  const filtered = tab === 'all' ? bookings : bookings.filter((b) => b.status === tab);
  const totalValue = bookings.filter((b) => b.status !== 'cancelled').reduce((sum, b) => sum + b.price, 0);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink">My Bookings</h1>
          <p className="mt-1.5 text-[15px] text-muted">
            Demonstration bookings — no payments are processed and nothing is reserved.
          </p>
        </div>
        <Button icon={<PlusIcon className="h-4 w-4" />} onClick={() => setNewBooking(true)}>
          New mock booking
        </Button>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="p-4">
          <p className="text-[12.5px] text-muted">Active bookings</p>
          <p className="mt-1 text-xl font-bold text-ink">{bookings.filter((b) => b.status === 'upcoming').length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[12.5px] text-muted">Total value</p>
          <p className="mt-1 text-xl font-bold text-ink">{inr(totalValue)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[12.5px] text-muted">Completed trips</p>
          <p className="mt-1 text-xl font-bold text-ink">{bookings.filter((b) => b.status === 'completed').length}</p>
        </Card>
      </div>

      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
        { id: 'all', label: 'All', count: bookings.length },
        { id: 'upcoming', label: 'Upcoming', count: bookings.filter((b) => b.status === 'upcoming').length },
        { id: 'completed', label: 'Completed', count: bookings.filter((b) => b.status === 'completed').length },
        { id: 'cancelled', label: 'Cancelled', count: bookings.filter((b) => b.status === 'cancelled').length }]
        } />
      

      {filtered.length === 0 ?
      <EmptyState
        icon={<CalendarCheckIcon className="h-5 w-5" />}
        title="No bookings in this view"
        description="Book a generated itinerary to see the confirmation, QR code and booking ID here." /> :


      <div className="space-y-4">
          {filtered.map((booking) =>
        <BookingCard
          key={booking.id}
          booking={booking}
          onView={() => setDetails(booking)}
          onCancel={() => setCancelTarget(booking)} />

        )}
        </div>
      }

      <Modal open={Boolean(details)} onClose={() => setDetails(null)} title={details?.title ?? ''} size="lg">
        {details &&
        <div className="space-y-4">
            <img src={details.image} alt="" className="h-44 w-full rounded-2xl object-cover" />
            <Badge tone={details.status === 'upcoming' ? 'brand' : details.status === 'completed' ? 'success' : 'danger'}>
              {details.status}
            </Badge>
            <dl className="divide-y divide-line rounded-2xl border border-line text-[13.5px]">
              {[
            ['Booking ID', details.reference],
            ['Type', details.type],
            ['Date', formatDate(details.date)],
            ['Travellers', String(details.travelers)],
            ['Amount', inr(details.price)]].
            map(([label, value]) =>
            <div key={label} className="flex justify-between px-4 py-3">
                  <dt className="text-muted">{label}</dt>
                  <dd className="font-semibold text-ink">{value}</dd>
                </div>
            )}
            </dl>
          </div>
        }
      </Modal>

      <Modal
        open={Boolean(cancelTarget)}
        onClose={() => setCancelTarget(null)}
        title="Cancel this booking?"
        description="Cancellation is free up to 48 hours before the start date in this prototype."
        footer={
        <>
            <Button variant="ghost" onClick={() => setCancelTarget(null)}>
              Keep booking
            </Button>
            <Button
            variant="danger"
            onClick={() => {
              if (cancelTarget) cancelBooking(cancelTarget.id);
              setCancelTarget(null);
            }}>
            
              Cancel booking
            </Button>
          </>
        }>
        
        <p className="text-[14px] text-muted">{cancelTarget?.title}</p>
      </Modal>

      <BookingFlow
        open={newBooking}
        onClose={() => setNewBooking(false)}
        item={{
          title: 'Jaipur · Heritage Weekend',
          type: 'Package',
          date: '2026-10-09',
          price: 32400,
          travelers: 2,
          image: IMAGES.jaipur
        }} />
      
    </div>);

}
