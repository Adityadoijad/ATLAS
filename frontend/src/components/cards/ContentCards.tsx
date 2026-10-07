import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  ArrowRightIcon,
  CalendarDaysIcon,
  ClockIcon,
  CloudSunIcon,
  HeartIcon,
  ImageOffIcon,
  MapPinIcon,
  SparklesIcon,
  StarIcon,
  UsersIcon,
  WalletIcon } from
'lucide-react';
import { Activity, Booking, LostFoundItem, Restaurant, SavedPlace, Trip } from '../../types';
import { Badge, Button, Card } from '../ui/Primitives';
import { DestinationImage } from './DestinationImage';
import { cn, formatDate, formatRange, inr } from '../../utils/format';
import { WeatherOutlook, outlookCaption } from '../../utils/weatherOutlook';
import { downloadBookingTicket } from '../../services/atlasApi';
import { useAtlas } from '../../contexts/AtlasContext';

export function StatsCard({
  label,
  value,
  icon,
  trend





}: {label: string;value: string;icon: React.ReactNode;trend?: string;}) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand/10 text-brand">{icon}</span>
        {trend && <span className="text-[12px] font-medium text-success">{trend}</span>}
      </div>
      <p className="mt-4 text-2xl font-bold text-ink">{value}</p>
      <p className="text-[13px] text-muted">{label}</p>
    </Card>);

}

export function RestaurantCard({ restaurant }: {restaurant: Restaurant;}) {
  const { isSaved, toggleSaved, toast } = useAtlas();
  const saved = isSaved(restaurant.id);
  return (
    <motion.article
      whileHover={{ y: -3 }}
      className="flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
      
      <div className="relative h-40 overflow-hidden">
        <img src={restaurant.image} alt={restaurant.name} loading="lazy" className="h-full w-full object-cover" />
        <span className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-brand px-2.5 py-1 text-[11px] font-semibold text-white">
          <SparklesIcon className="h-3 w-3" /> ATLAS pick
        </span>
        <button
          onClick={() => toggleSaved(restaurant.id, restaurant.name)}
          aria-label={saved ? 'Remove from saved' : 'Save restaurant'}
          className="absolute right-3 top-3 rounded-full bg-white/90 p-2 text-slate-600 shadow-sm">
          
          <HeartIcon className={cn('h-4 w-4', saved && 'fill-danger text-danger')} />
        </button>
      </div>
      <div className="flex flex-1 flex-col p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-[15px] font-bold text-ink">{restaurant.name}</h3>
            <p className="text-[13px] text-muted">{restaurant.cuisine} · {restaurant.city}</p>
          </div>
          <span className="inline-flex items-center gap-1 text-[13px] font-semibold text-ink">
            <StarIcon className="h-3.5 w-3.5 fill-warning text-warning" />
            {restaurant.rating}
          </span>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {restaurant.tags.slice(0, 3).map((tag) =>
          <Badge key={tag}>{tag}</Badge>
          )}
        </div>
        <p className="mt-3 rounded-xl bg-brand/5 p-3 text-[12.5px] leading-relaxed text-muted">
          <span className="font-semibold text-brand">Why ATLAS recommends it · </span>
          {restaurant.aiReason}
        </p>
        <div className="mt-auto flex items-center justify-between pt-4 text-[13px]">
          <span className="text-muted">{restaurant.distanceKm} km · {inr(restaurant.pricePerPerson)} pp</span>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => toast({ title: 'Added to trip', description: `${restaurant.name} added to Day 2.`, tone: 'success' })}>
            
            Add to Trip
          </Button>
        </div>
      </div>
    </motion.article>);

}

export function ActivityCard({ activity }: {activity: Activity;}) {
  const { isSaved, toggleSaved, toast } = useAtlas();
  const saved = isSaved(activity.id);
  return (
    <motion.article
      whileHover={{ y: -3 }}
      className="flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
      
      <div className="relative h-40 overflow-hidden">
        <img src={activity.image} alt={activity.name} loading="lazy" className="h-full w-full object-cover" />
        <span className="absolute left-3 top-3 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-slate-800">
          {activity.category}
        </span>
        <button
          onClick={() => toggleSaved(activity.id, activity.name)}
          aria-label={saved ? 'Remove from saved' : 'Save activity'}
          className="absolute right-3 top-3 rounded-full bg-white/90 p-2 text-slate-600 shadow-sm">
          
          <HeartIcon className={cn('h-4 w-4', saved && 'fill-danger text-danger')} />
        </button>
      </div>
      <div className="flex flex-1 flex-col p-4">
        <h3 className="text-[15px] font-bold text-ink">{activity.name}</h3>
        <p className="mt-0.5 flex items-center gap-1 text-[13px] text-muted">
          <MapPinIcon className="h-3.5 w-3.5" /> {activity.location}
        </p>
        <div className="mt-3 grid grid-cols-2 gap-y-1.5 text-[12.5px] text-muted">
          <span className="inline-flex items-center gap-1.5">
            <StarIcon className="h-3.5 w-3.5 fill-warning text-warning" /> {activity.rating} ({activity.reviews})
          </span>
          <span className="inline-flex items-center gap-1.5">
            <ClockIcon className="h-3.5 w-3.5" /> {activity.duration}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <WalletIcon className="h-3.5 w-3.5" /> {activity.price === 0 ? 'Free entry' : inr(activity.price)}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <CalendarDaysIcon className="h-3.5 w-3.5" /> {activity.hours}
          </span>
        </div>
        <p className="mt-3 rounded-xl bg-accent/5 p-3 text-[12.5px] leading-relaxed text-muted">
          <span className="font-semibold text-[#0E7490] dark:text-accent">AI reason · </span>
          {activity.aiReason}
        </p>
        <div className="mt-auto flex gap-2 pt-4">
          <Button
            size="sm"
            className="flex-1"
            onClick={() => toast({ title: 'Added to trip', description: `${activity.name} scheduled.`, tone: 'success' })}>
            
            Add to Trip
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => toast({ title: activity.name, description: activity.aiReason, tone: 'info' })}>
            
            Details
          </Button>
        </div>
      </div>
    </motion.article>);

}

export function TripCard({
  trip,
  onView,
  onDelete




}: {trip: Trip;onView: () => void;onDelete: () => void;}) {
  const { toast } = useAtlas();
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col sm:flex-row">
        <DestinationImage destination={trip.destination} src={trip.image} className="h-40 w-full sm:h-auto sm:w-48" />
        <div className="flex flex-1 flex-col p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-ink">
                {trip.destination}, {trip.country}
              </h3>
              <p className="mt-1 text-[13px] text-muted">{formatRange(trip.startDate, trip.endDate)}</p>
            </div>
            <Badge tone={trip.status === 'upcoming' ? 'brand' : trip.status === 'past' ? 'neutral' : 'accent'}>
              {trip.status === 'upcoming' ? 'Upcoming' : trip.status === 'past' ? 'Completed' : 'Saved plan'}
            </Badge>
          </div>

          <div className="mt-3 flex flex-wrap gap-4 text-[13px] text-muted">
            <span className="inline-flex items-center gap-1.5">
              <UsersIcon className="h-3.5 w-3.5" /> {trip.travelers} travellers
            </span>
            <span className="inline-flex items-center gap-1.5">
              <WalletIcon className="h-3.5 w-3.5" /> {inr(trip.budget)}
            </span>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <Button size="sm" onClick={onView}>
              View Trip
            </Button>
            <Button size="sm" variant="secondary" onClick={() => toast({ title: 'Edit mode', description: 'Opening the planner with this trip loaded.', tone: 'info' })}>
              Edit
            </Button>
            <Button size="sm" variant="ghost" onClick={() => toast({ title: 'Share link copied', tone: 'success' })}>
              Share
            </Button>
            <Button size="sm" variant="danger" onClick={onDelete}>
              Delete
            </Button>
          </div>
        </div>
      </div>
    </Card>);

}

export function BookingCard({
  booking,
  onView,
  onCancel




}: {booking: Booking;onView: () => void;onCancel: () => void;}) {
  const { toast } = useAtlas();
  const [downloading, setDownloading] = useState(false);

  // Only a persisted booking has a server record to issue a ticket from.
  const canDownload = Boolean(booking.persisted);

  const downloadTicket = async () => {
    const token = localStorage.getItem('atlas_access_token');
    if (!token) return;
    setDownloading(true);
    try {
      await downloadBookingTicket(booking.id, token);
    } catch (reason) {
      toast({
        title: 'Could not generate the E-Ticket',
        description: reason instanceof Error ? reason.message : 'Please try again.',
        tone: 'error'
      });
    } finally {
      setDownloading(false);
    }
  };
  const tone = booking.status === 'upcoming' ? 'brand' : booking.status === 'completed' ? 'success' : 'danger';
  return (
    <Card className="overflow-hidden">
      <div className="flex flex-col sm:flex-row sm:items-center">
        <img src={booking.image} alt="" className="h-36 w-full object-cover sm:h-24 sm:w-32 sm:rounded-xl sm:m-4" />
        <div className="flex-1 p-4 sm:py-4 sm:pl-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-[15px] font-bold text-ink">{booking.title}</h3>
            <Badge tone={tone}>{booking.status}</Badge>
          </div>
          <p className="mt-1 text-[13px] text-muted">
            {booking.type} · {formatDate(booking.date)} · {booking.travelers} traveller{booking.travelers > 1 ? 's' : ''}
          </p>
          <p className="mt-1 font-mono text-[12px] text-muted">Booking ID {booking.reference}</p>
        </div>
        <div className="flex flex-col items-start gap-2 p-4 sm:items-end">
          <span className="text-base font-bold text-ink">{inr(booking.price)}</span>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" onClick={onView}>
              View Details
            </Button>
            {canDownload &&
            <Button
              size="sm"
              variant="ghost"
              loading={downloading}
              onClick={downloadTicket}>

                Download E-Ticket
              </Button>
            }
            {booking.status === 'upcoming' &&
            <Button size="sm" variant="danger" onClick={onCancel}>
                Cancel
              </Button>
            }
          </div>
        </div>
      </div>
    </Card>);

}

/**
 * Weather from OpenWeatherMap, or an honest statement that there is none.
 *
 * Every branch below is driven by `outlook`, which is decided in
 * `utils/weatherOutlook`. There is deliberately no default case that renders
 * numbers: if the provider did not supply a day, no day is drawn.
 */
export function WeatherCard({ outlook }: {outlook: WeatherOutlook;}) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-[15px] font-bold text-ink">Weather outlook</h3>
        <CloudSunIcon className="h-5 w-5 text-accent" />
      </div>

      {outlook.kind === 'no-trip' &&
      <p className="mt-3 text-[13px] text-muted">
          Plan a trip and the forecast for your destination will appear here.
        </p>
      }

      {outlook.kind === 'loading' &&
      <div className="mt-4 grid grid-cols-5 gap-2">
          {[0, 1, 2, 3, 4].map((slot) =>
        <div key={slot} className="h-[68px] animate-pulse rounded-xl bg-canvas" />
        )}
        </div>
      }

      {outlook.kind === 'unavailable' &&
      <div className="mt-3">
          <p className="text-[13px] font-semibold text-ink">Live weather unavailable</p>
          <p className="mt-1 text-[12.5px] text-muted">{outlook.reason}</p>
          <p className="mt-2 text-[12px] text-muted">
            Nothing is shown for {outlook.destination} rather than an estimate.
          </p>
        </div>
      }

      {outlook.kind === 'forecast' &&
      <>
          <div className="mt-4 grid grid-cols-5 gap-2">
            {outlook.days.slice(0, 5).map((day) =>
          <div key={day.date} className="rounded-xl bg-canvas p-2.5 text-center">
                <p className="text-[11px] font-medium text-muted">{day.weekday}</p>
                <p className="mt-1 text-base font-bold text-ink">{Math.round(day.temperatureC)}°</p>
                <p className="text-[10px] text-muted">
                  {Math.round(day.temperatureMinC)}°–{Math.round(day.temperatureMaxC)}°
                </p>
                <p className="mt-0.5 text-[10px] capitalize leading-tight text-muted">{day.condition}</p>
              </div>
          )}
          </div>
          <p
        className={cn(
          'mt-4 rounded-xl p-3 text-[12.5px]',
          outlook.coversTripDates ?
          'bg-success/10 text-[#047857] dark:text-success' :
          'bg-warning/10 text-[#B45309] dark:text-warning'
        )}>

            {outlookCaption(outlook)}
          </p>
          <p className="mt-2 text-[11px] text-muted">Live weather · OpenWeatherMap</p>
        </>
      }
    </Card>);

}

export function BudgetCard({
  budget,
  spent,
  breakdown




}: {budget: number;spent: number;breakdown: {label: string;value: number;}[];}) {
  const pct = Math.min(100, Math.round(spent / budget * 100));
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-[15px] font-bold text-ink">Budget overview</h3>
        <Badge tone="success">{inr(budget - spent)} left</Badge>
      </div>
      <p className="mt-3 text-2xl font-bold text-ink">{inr(spent)}</p>
      <p className="text-[13px] text-muted">of {inr(budget)} planned</p>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-subtle">
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} className="h-full rounded-full bg-brand" />
      </div>
      <ul className="mt-4 space-y-2">
        {breakdown.map((b) =>
        <li key={b.label} className="flex items-center justify-between text-[13px]">
            <span className="text-muted">{b.label}</span>
            <span className="font-semibold text-ink">{inr(b.value)}</span>
          </li>
        )}
      </ul>
    </Card>);

}

export function LostFoundCard({ item, onContact }: {item: LostFoundItem;onContact: () => void;}) {
  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <div className="relative h-36">
        {item.image ?
        <img
          src={item.image}
          alt={item.isRepresentative ? `Representative photo of a ${item.title.toLowerCase()}` : item.title}
          loading="lazy"
          className="h-full w-full object-cover" /> :

        // No photo was attached. A category placeholder makes that obvious;
        // a stand-in picture of some other object would invite false matches.
        <div className="flex h-full w-full flex-col items-center justify-center gap-1.5 bg-gradient-to-br from-brand/10 to-accent/10">
            <ImageOffIcon className="h-5 w-5 text-muted" />
            <span className="text-[11px] font-medium text-muted">{item.category} · no photo</span>
          </div>
        }
        <span
          className={cn(
            'absolute left-3 top-3 rounded-full px-2.5 py-1 text-[11px] font-semibold text-white',
            item.type === 'lost' ? 'bg-danger' : 'bg-success'
          )}>
          
          {item.type === 'lost' ? 'Lost' : 'Found'}
        </span>
        {/* Says plainly that this is not a photo of the actual item, so nobody
            "recognises" a stock image as their own property. */}
        {item.image && item.isRepresentative &&
        <span className="absolute right-3 top-3 rounded-full bg-black/55 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
            Representative image
          </span>
        }
        {/* CC-licensed photos must credit their author. */}
        {item.imageCredit && (item.imageCredit.author || item.imageCredit.license) &&
        <div className="absolute inset-x-0 bottom-0 truncate bg-black/50 px-2.5 py-1 text-[9px] text-white/80 backdrop-blur-sm">
            {item.imageCredit.sourceUrl ?
          <a
            href={item.imageCredit.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white">

                {[item.imageCredit.author, item.imageCredit.license].filter(Boolean).join(' · ')}
              </a> :

          [item.imageCredit.author, item.imageCredit.license].filter(Boolean).join(' · ')
          }
          </div>
        }
      </div>
      <div className="flex flex-1 flex-col p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-[15px] font-bold text-ink">{item.title}</h3>
          <Badge tone={item.status === 'Open' ? 'warning' : item.status === 'Matched' ? 'brand' : 'success'}>
            {item.status}
          </Badge>
        </div>
        <p className="mt-1 flex items-center gap-1 text-[13px] text-muted">
          <MapPinIcon className="h-3.5 w-3.5" /> {item.location} · {formatDate(item.date)}
        </p>
        <p className="mt-2 line-clamp-2 text-[13px] leading-relaxed text-muted">{item.description}</p>
        <div className="mt-auto flex gap-2 pt-4">
          <Button size="sm" variant="secondary" onClick={onContact}>
            Contact
          </Button>
          <Button size="sm" variant="ghost" onClick={onContact} icon={<ArrowRightIcon className="h-3.5 w-3.5" />}>
            Report Match
          </Button>
        </div>
      </div>
    </Card>);

}

export function SavedPlaceCard({ place, onRemove }: {place: SavedPlace;onRemove: () => void;}) {
  const { toast } = useAtlas();
  return (
    <Card className="flex h-full flex-col overflow-hidden">
      <img src={place.image} alt="" className="h-36 w-full object-cover" />
      <div className="flex flex-1 flex-col p-4">
        <h3 className="text-[15px] font-bold text-ink">{place.name}</h3>
        <p className="mt-0.5 text-[13px] text-muted">{place.subtitle}</p>
        <span className="mt-2 inline-flex w-fit items-center gap-1 text-[13px] font-semibold text-ink">
          <StarIcon className="h-3.5 w-3.5 fill-warning text-warning" /> {place.rating}
        </span>
        <div className="mt-auto flex gap-2 pt-4">
          <Button size="sm" onClick={() => toast({ title: 'Added to trip', description: `${place.name} added.`, tone: 'success' })}>
            Add to Trip
          </Button>
          <Button size="sm" variant="ghost" onClick={onRemove}>
            Remove
          </Button>
        </div>
      </div>
    </Card>);

}