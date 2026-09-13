import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRightIcon,
  BookmarkIcon,
  CheckCircle2Icon,
  LuggageIcon,
  MapPinIcon,
  PlusIcon,
  SparklesIcon,
  TrendingUpIcon } from
'lucide-react';
import { BudgetCard, StatsCard, WeatherCard } from '../components/cards/ContentCards';
import { DestinationCard } from '../components/cards/DestinationCard';
import { DiscoverMore } from '../components/discover/DiscoverMore';
import { Badge, Button, Card, SectionHeading, Skeleton } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';
import { fetchRecommendations } from '../services/atlasApi';
import { RecommendedDestination } from '../types';
import { formatRange, inr } from '../utils/format';

const activity = [
{ label: 'Planner Agent generated a 5-day Goa itinerary', time: '2 hours ago' },
{ label: 'You saved Sakura Izakaya to Restaurants', time: 'Yesterday' },
{ label: 'Budget Optimizer trimmed ₹4,200 from the Kyoto plan', time: '2 days ago' },
{ label: 'Booking ATL-9F2K41 confirmed', time: '4 days ago' }];


const insights = [
{ label: 'Most-planned month', value: 'November' },
{ label: 'Average trip length', value: '5.4 days' },
{ label: 'Preferred pace', value: 'Moderate' },
{ label: 'Top interest', value: 'Food & Culture' }];


export function DashboardPage() {
  const { trips, bookings, savedItems } = useAtlas();
  const navigate = useNavigate();
  const upcoming = trips.find((t) => t.status === 'upcoming');

  const [recommendations, setRecommendations] = useState<RecommendedDestination[]>([]);
  const [recommendationsLoading, setRecommendationsLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const token = localStorage.getItem('atlas_access_token');
    if (!token) {
      setRecommendationsLoading(false);
      return;
    }
    fetchRecommendations(token).
    then((data) => {
      if (active) setRecommendations(data);
    }).
    catch(() => {
      if (active) setRecommendations([]);
    }).
    finally(() => {
      if (active) setRecommendationsLoading(false);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-ink">Good morning, Explorer.</h1>
          <p className="mt-1.5 text-[15px] text-muted">Here is where your travel planning stands today.</p>
        </div>
        <Button icon={<PlusIcon className="h-4 w-4" />} onClick={() => navigate('/plan')}>
          Plan a New Trip
        </Button>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard label="Upcoming trips" value={String(trips.filter((t) => t.status === 'upcoming').length)} icon={<LuggageIcon className="h-5 w-5" />} trend="+1 this month" />
        <StatsCard label="Active plans" value={String(trips.filter((t) => t.progress < 100).length)} icon={<SparklesIcon className="h-5 w-5" />} />
        <StatsCard label="Saved places" value={String(savedItems.length)} icon={<BookmarkIcon className="h-5 w-5" />} />
        <StatsCard label="Completed trips" value={String(trips.filter((t) => t.status === 'past').length)} icon={<CheckCircle2Icon className="h-5 w-5" />} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
        <div className="space-y-5">
          {upcoming &&
          <Card className="overflow-hidden">
              <div className="relative h-48">
                <img src={upcoming.image} alt={upcoming.destination} className="h-full w-full object-cover" />
                <div className="absolute inset-0 bg-slate-900/40" />
                <div className="absolute inset-x-0 bottom-0 flex flex-wrap items-end justify-between gap-3 p-5">
                  <div>
                    <Badge tone="brand" className="bg-white/90 text-brand">
                      Next trip
                    </Badge>
                    <h2 className="mt-2 font-display text-2xl font-bold text-white">
                      {upcoming.destination}, {upcoming.country}
                    </h2>
                    <p className="text-[13.5px] text-white/85">
                      {formatRange(upcoming.startDate, upcoming.endDate)} · {upcoming.travelers} travellers · {inr(upcoming.budget)}
                    </p>
                  </div>
                  <Link
                  to="/itinerary"
                  className="inline-flex h-10 items-center gap-2 rounded-xl bg-white px-4 text-[13.5px] font-semibold text-brand">
                  
                    View itinerary <ArrowRightIcon className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
              <div className="flex items-center gap-4 p-4">
                <div className="flex-1">
                  <div className="flex justify-between text-[12.5px] text-muted">
                    <span>Planning progress</span>
                    <span className="font-semibold text-ink">{upcoming.progress}%</span>
                  </div>
                  <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-subtle">
                    <div className="h-full rounded-full bg-brand" style={{ width: `${upcoming.progress}%` }} />
                  </div>
                </div>
              </div>
            </Card>
          }

          <section>
            <SectionHeading
              title="AI recommendations"
              subtitle="Fresh matches based on your saved places and past trips."
              action={
              <Link to="/explore" className="text-[13px] font-semibold text-brand hover:underline">
                  View all
                </Link>
              } />
            
            {recommendationsLoading ?
            <div className="mt-5 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {Array.from({ length: 3 }).map((_, i) =>
              <Card key={i} className="overflow-hidden p-0">
                    <Skeleton className="h-40 rounded-none" />
                    <div className="space-y-2 p-4">
                      <Skeleton className="h-4 w-2/3" />
                      <Skeleton className="h-3 w-1/3" />
                    </div>
                  </Card>
              )}
              </div> :
            recommendations.length === 0 ?
            <p className="mt-5 text-[13px] text-muted">Log in to see recommendations personalized to your trips and saved places.</p> :

            <div className="mt-5 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {recommendations.slice(0, 3).map((d) =>
              <div key={d.id}>
                    <DestinationCard destination={d} onClick={() => navigate(`/explore/${encodeURIComponent(d.name)}`)} />
                    <p className="mt-2 text-[12px] text-muted">{d.reason}</p>
                  </div>
              )}
              </div>
            }

            <DiscoverMore token={localStorage.getItem('atlas_access_token')} />
          </section>

          <Card className="p-5">
            <h2 className="text-[15px] font-bold text-ink">Recent activity</h2>
            <ul className="mt-4 space-y-3.5">
              {activity.map((a) =>
              <li key={a.label} className="flex items-start gap-3">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                  <div>
                    <p className="text-[13.5px] text-ink">{a.label}</p>
                    <p className="text-[12px] text-muted">{a.time}</p>
                  </div>
                </li>
              )}
            </ul>
          </Card>
        </div>

        <div className="space-y-5">
          <BudgetCard
            budget={trips.reduce((sum, t) => sum + t.budget, 0)}
            spent={bookings.filter((b) => b.status !== 'cancelled').reduce((sum, b) => sum + b.price, 0)}
            breakdown={[
            { label: 'Bookings paid', value: bookings.filter((b) => b.status === 'completed').reduce((s, b) => s + b.price, 0) },
            { label: 'Upcoming commitments', value: bookings.filter((b) => b.status === 'upcoming').reduce((s, b) => s + b.price, 0) },
            { label: 'Unallocated', value: 42000 }]
            } />
          

          <WeatherCard
            days={[
            { day: 'Mon', temp: 29, condition: 'Sunny' },
            { day: 'Tue', temp: 28, condition: 'Cloudy' },
            { day: 'Wed', temp: 27, condition: 'Rain' },
            { day: 'Thu', temp: 30, condition: 'Sunny' },
            { day: 'Fri', temp: 29, condition: 'Clear' }]
            } />
          

          <Card className="p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-[15px] font-bold text-ink">Travel insights</h2>
              <TrendingUpIcon className="h-4.5 w-4.5 text-brand" />
            </div>
            <ul className="mt-4 space-y-3">
              {insights.map((i) =>
              <li key={i.label} className="flex items-center justify-between text-[13px]">
                  <span className="text-muted">{i.label}</span>
                  <span className="font-semibold text-ink">{i.value}</span>
                </li>
              )}
            </ul>
            <p className="mt-4 flex items-start gap-2 rounded-xl bg-brand/5 p-3 text-[12.5px] text-muted">
              <MapPinIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" />
              You travel best on 5-day, food-led trips. ATLAS will bias future plans that way.
            </p>
          </Card>
        </div>
      </div>
    </div>);

}
