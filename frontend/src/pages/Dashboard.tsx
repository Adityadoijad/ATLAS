import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRightIcon,
  BookmarkIcon,
  CheckCircle2Icon,
  LuggageIcon,
  PlusIcon,
  SparklesIcon,
  TrendingUpIcon } from
'lucide-react';
import { BudgetCard, StatsCard, WeatherCard } from '../components/cards/ContentCards';
import { DestinationCard } from '../components/cards/DestinationCard';
import { DestinationImage } from '../components/cards/DestinationImage';
import { DiscoverMore } from '../components/discover/DiscoverMore';
import { Badge, Button, Card, SectionHeading, Skeleton } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';
import { fetchRecommendations } from '../services/atlasApi';
import { RecommendedDestination } from '../types';
import { formatRange, inr } from '../utils/format';
import { buildRecentActivity, buildTravelInsights, relativeTime } from '../utils/dashboard';
import { relevantTripForWeather, weatherOutlook } from '../utils/weatherOutlook';
import { useDestinationForecast } from '../hooks/useDestinationForecast';

export function DashboardPage() {
  const { trips, bookings, savedItems, authUser } = useAtlas();
  // The signed-in account's own name. "Explorer" is only for the moment before
  // the session resolves, or a signed-out visitor — never a stand-in for a
  // name ATLAS already knows.
  const firstName = authUser?.name?.trim().split(/\s+/)[0];
  const navigate = useNavigate();
  const upcoming = trips.find((t) => t.status === 'upcoming');
  // Derived from the user's own persisted trips and bookings. Empty until
  // they actually have some — never filled with sample figures.
  const activity = buildRecentActivity(trips, bookings);
  const insights = buildTravelInsights(trips);

  // Weather is about a real destination or it is about nothing: the soonest
  // trip that has not finished yet, fetched through the backend so the
  // OpenWeatherMap key stays server-side.
  const weatherTrip = relevantTripForWeather(trips);
  const forecast = useDestinationForecast(weatherTrip?.destination ?? null);
  const outlook = weatherOutlook(weatherTrip, forecast);

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
          <h1 className="font-display text-3xl font-bold text-ink">
            {firstName ? `Welcome back, ${firstName}.` : 'Welcome to ATLAS.'}
          </h1>
          <p className="mt-1.5 text-[15px] text-muted">Here is where your travel planning stands today.</p>
        </div>
        <Button icon={<PlusIcon className="h-4 w-4" />} onClick={() => navigate('/plan')}>
          Plan a New Trip
        </Button>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatsCard label="Upcoming trips" value={String(trips.filter((t) => t.status === 'upcoming').length)} icon={<LuggageIcon className="h-5 w-5" />} />
        <StatsCard label="Bookings" value={String(bookings.filter((b) => b.status !== 'cancelled').length)} icon={<SparklesIcon className="h-5 w-5" />} />
        <StatsCard label="Saved places" value={String(savedItems.length)} icon={<BookmarkIcon className="h-5 w-5" />} />
        <StatsCard label="Completed trips" value={String(trips.filter((t) => t.status === 'past').length)} icon={<CheckCircle2Icon className="h-5 w-5" />} />
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
        <div className="space-y-5">
          {upcoming &&
          <Card className="overflow-hidden">
              <div className="relative h-48">
                <DestinationImage destination={upcoming.destination} src={upcoming.image} className="h-full w-full" />
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
            {activity.length === 0 ?
            <p className="mt-3 text-[13px] text-muted">
                No recent activity yet. Planning a trip or making a booking will show up here.
              </p> :

            <ul className="mt-4 space-y-3.5">
                {activity.map((a) =>
              <li key={a.id} className="flex items-start gap-3">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                    <div>
                      <p className="text-[13.5px] text-ink">{a.label}</p>
                      <p className="text-[12px] text-muted">{relativeTime(a.at)}</p>
                    </div>
                  </li>
              )}
              </ul>
            }
          </Card>
        </div>

        <div className="space-y-5">
          <BudgetCard
            budget={trips.reduce((sum, t) => sum + t.budget, 0)}
            spent={bookings.filter((b) => b.status !== 'cancelled').reduce((sum, b) => sum + b.price, 0)}
            breakdown={[
            { label: 'Bookings paid', value: bookings.filter((b) => b.status === 'completed').reduce((s, b) => s + b.price, 0) },
            { label: 'Upcoming commitments', value: bookings.filter((b) => b.status === 'upcoming').reduce((s, b) => s + b.price, 0) },
            {
              label: 'Unallocated',
              value: Math.max(
                0,
                trips.reduce((sum, t) => sum + t.budget, 0) -
                bookings.filter((b) => b.status !== 'cancelled').reduce((sum, b) => sum + b.price, 0)
              )
            }]
            } />
          

          <WeatherCard outlook={outlook} />

          <Card className="p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-[15px] font-bold text-ink">Travel insights</h2>
              <TrendingUpIcon className="h-4.5 w-4.5 text-brand" />
            </div>
            {insights.length === 0 ?
            <p className="mt-3 text-[13px] text-muted">
                Travel insights will appear once you have planned a trip.
              </p> :

            <ul className="mt-4 space-y-3">
                {insights.map((i) =>
              <li key={i.label} className="flex items-center justify-between text-[13px]">
                    <span className="text-muted">{i.label}</span>
                    <span className="font-semibold text-ink">{i.value}</span>
                  </li>
              )}
              </ul>
            }
          </Card>
        </div>
      </div>
    </div>);

}
