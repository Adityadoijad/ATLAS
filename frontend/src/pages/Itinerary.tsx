import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ChevronDownIcon,
  DownloadIcon,
  PencilIcon,
  RefreshCwIcon,
  SaveIcon,
  Share2Icon,
  SparklesIcon,
  TicketIcon,
  UsersIcon,
  WalletIcon } from
'lucide-react';
import { ItineraryTimeline, MapCard } from '../components/itinerary/Timeline';
import { FoodPlace, FoodPlacesCard } from '../components/itinerary/FoodPlacesCard';
import { BudgetCard, CommunityInsight, WeatherCard } from '../components/cards/ContentCards';
import { BookingFlow } from '../components/booking/BookingFlow';
import { Badge, Button, Card, EmptyState, Skeleton } from '../components/ui/Primitives';
import { useAtlas } from '../contexts/AtlasContext';
import { fetchLatestTripPlan, generateTripPlan, persistTripPlan } from '../services/atlasApi';
import { formatRange, inr } from '../utils/format';
import { buildGoogleMapsDirectionsUrl, limitRouteStops, routeStopsFromDays } from '../utils/googleMaps';

export function ItineraryPage() {
  const { plan, setPlan, toast } = useAtlas();
  const [regenerating, setRegenerating] = useState(false);
  const [explanationOpen, setExplanationOpen] = useState(true);
  const [bookingOpen, setBookingOpen] = useState(false);
  const navigate = useNavigate();

  const [restoring, setRestoring] = useState(!plan);

  // Arriving here without a plan in context (a refresh, or a direct link)
  // restores the traveller's most recent saved trip. It must never generate a
  // stand-in trip for some other destination — showing a Goa itinerary to
  // someone who planned Raipur is worse than showing nothing.
  useEffect(() => {
    if (plan) return;
    const token = localStorage.getItem('atlas_access_token');
    if (!token) {
      setRestoring(false);
      return;
    }
    let cancelled = false;
    setRestoring(true);
    fetchLatestTripPlan(token).
    then((latest) => {
      if (!cancelled && latest) setPlan(latest);
    }).
    catch(() => {/* fall through to the empty state below */}).
    finally(() => {
      if (!cancelled) setRestoring(false);
    });
    return () => {
      cancelled = true;
    };
  }, [plan, setPlan]);

  if (!plan && restoring) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-52" />
        <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </div>);

  }

  if (!plan) {
    return (
      <EmptyState
        icon={<SparklesIcon className="h-6 w-6" />}
        title="No itinerary yet"
        description="Plan a trip and ATLAS will build a day-by-day itinerary for your destination."
        action={<Button onClick={() => navigate('/plan')}>Plan a New Trip</Button>} />);


  }

  const regenerate = async () => {
    setRegenerating(true);
    const next = await generateTripPlan({
      destination: plan.destination,
      startDate: plan.startDate,
      endDate: plan.endDate,
      adults: plan.travelers,
      children: 0,
      interests: ['Nature', 'Food'],
      transport: ['Local Transport'],
      accommodation: ['Hotel'],
      food: ['Local cuisine'],
      accessibility: [],
      budget: plan.budget,
      currency: 'INR',
      flexibleBudget: true,
      notes: ''
    });
    setPlan(next);
    setRegenerating(false);
    toast({ title: 'Itinerary regenerated', description: 'Agents re-ran with the same constraints.', tone: 'success' });
  };

  const saveTrip = async () => {
    const token = localStorage.getItem('atlas_access_token');
    if (!token) {
      navigate('/login');
      return;
    }
    try {
      await persistTripPlan(plan, token);
      toast({ title: 'Trip saved', description: 'Added to My Trips.', tone: 'success' });
    } catch (error) {
      toast({ title: 'Could not save trip', description: error instanceof Error ? error.message : undefined, tone: 'error' });
    }
  };

  // Looked up by label rather than index so the tiles can't silently drift
  // out of sync with the breakdown order.
  const breakdownFor = (label: string) =>
  plan.breakdown.find((entry) => entry.label === label)?.value ?? 0;

  // All four categories are shown, so these add up to the estimated total.
  const summary = [
  { label: 'Estimated total cost', value: inr(plan.estimatedCost) },
  { label: 'Accommodation', value: inr(breakdownFor('Accommodation')) },
  { label: 'Travel', value: inr(breakdownFor('Travel')) },
  { label: 'Food', value: inr(breakdownFor('Food')) },
  { label: 'Activities', value: inr(breakdownFor('Activities')) },
  { label: 'Remaining budget', value: inr(plan.budget - plan.estimatedCost) }];

  // Report what is actually live vs estimated, per source. The overall
  // is_realtime_data flag is always false while Hotel/Food have no live
  // provider wired, so using it alone would wrongly blame weather and maps.
  const dataStatus = (() => {
    const context = plan.data_context as
    Record<string, {is_realtime_data?: boolean;cost_is_estimated?: boolean;} | undefined> |
    undefined;
    if (!context) return null;

    const liveLabels: string[] = [];
    // Two different claims, phrased differently: Route/Weather/Food degrade to
    // estimated *information*, while Hotel/Food costs are always estimated
    // money. Food appears in both — OpenStreetMap tells us which restaurants
    // exist, but publishes no prices, so its places can be live while its
    // meal cost stays an AI estimate.
    const estimatedCostLabels: string[] = [];
    const estimatedDataLabels: string[] = [];

    ([
    ['route', 'Route', 'data'],
    ['weather', 'Weather', 'data'],
    ['hotel', 'Hotel', 'cost'],
    ['food', 'Food', 'data']] as const).
    forEach(([key, label, kind]) => {
      const agent = context[key];
      if (!agent || typeof agent.is_realtime_data !== 'boolean') return;
      if (agent.is_realtime_data) {
        liveLabels.push(label);
      } else if (kind === 'cost') {
        estimatedCostLabels.push(label);
      } else {
        estimatedDataLabels.push(label);
      }
      // An agent that sources real information but cannot source real prices
      // reports both facts, so the banner never implies the money is live.
      if (agent.cost_is_estimated && !estimatedCostLabels.includes(label)) {
        estimatedCostLabels.push(label);
      }
    });

    if (estimatedCostLabels.length === 0 && estimatedDataLabels.length === 0) return null;
    return { liveLabels, estimatedCostLabels, estimatedDataLabels };
  })();

  // Only rendered when the Food agent actually reached OpenStreetMap; a
  // fallback run carries no places and the card disappears entirely.
  const foodPlaces = (() => {
    const food = (plan.data_context as Record<string, {places?: FoodPlace[];} | undefined> | undefined)?.food;
    return Array.isArray(food?.places) ? food.places : [];
  })();

  // The route's real stops, taken from the itinerary's own activity locations.
  // The Route agent only geocodes the destination city, so there are no
  // per-stop coordinates to use — Google Maps receives place names instead.
  // Listed and linked from the same set, so the card shows exactly the route
  // the Google Maps link opens.
  const routeStops = limitRouteStops(routeStopsFromDays(plan.days, plan.destination));
  const directionsUrl = buildGoogleMapsDirectionsUrl(routeStops);

  const formatLabels = (labels: string[]) =>
  labels.length <= 1 ?
  labels.join('') :
  `${labels.slice(0, -1).join(', ')} and ${labels[labels.length - 1]}`;

  return (
    <div className="space-y-6">
      {dataStatus &&
      <div
        role="status"
        className="rounded-xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm font-medium text-[#92400E] dark:text-warning">
        {dataStatus.liveLabels.length > 0 &&
        <>{formatLabels(dataStatus.liveLabels)} data {dataStatus.liveLabels.length === 1 ? 'is' : 'are'} live. </>
        }
        {dataStatus.estimatedDataLabels.length > 0 &&
        <>
            {formatLabels(dataStatus.estimatedDataLabels)} data{' '}
            {dataStatus.estimatedDataLabels.length === 1 ? 'is' : 'are'} currently estimated.{' '}
          </>
        }
        {dataStatus.estimatedCostLabels.length > 0 &&
        <>
            {formatLabels(dataStatus.estimatedCostLabels)}{' '}
            {dataStatus.estimatedCostLabels.length === 1 ? 'cost is an AI estimate' : 'costs are AI estimates'}.
          </>
        }
      </div>
      }
      <Card className="overflow-hidden">
        <div className="relative h-44 sm:h-56">
          <img src={plan.image} alt={plan.destination} className="h-full w-full object-cover" />
          <div className="absolute inset-0 bg-slate-900/45" />
          <div className="absolute inset-x-0 bottom-0 p-6">
            <Badge tone="brand" className="bg-white/90 text-brand">
              <SparklesIcon className="h-3 w-3" /> Generated by 9 agents
            </Badge>
            <h1 className="mt-3 font-display text-3xl font-bold text-white sm:text-4xl">Your Personalized Trip</h1>
            <p className="mt-1 text-[14px] text-white/85">
              {plan.destination}, {plan.country} · {formatRange(plan.startDate, plan.endDate)} · {plan.travelers} travellers ·{' '}
              {inr(plan.budget)} budget
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2 border-t border-line p-4">
          <Button size="sm" icon={<TicketIcon className="h-3.5 w-3.5" />} onClick={() => setBookingOpen(true)}>
            Book this trip
          </Button>
          <Button size="sm" variant="secondary" icon={<PencilIcon className="h-3.5 w-3.5" />} onClick={() => navigate('/plan')}>
            Modify Trip
          </Button>
          <Button size="sm" variant="secondary" loading={regenerating} icon={<RefreshCwIcon className="h-3.5 w-3.5" />} onClick={regenerate}>
            Regenerate
          </Button>
          <Button
            size="sm"
            variant="secondary"
            icon={<SaveIcon className="h-3.5 w-3.5" />}
            onClick={saveTrip}>
            
            Save Trip
          </Button>
          <Button
            size="sm"
            variant="ghost"
            icon={<Share2Icon className="h-3.5 w-3.5" />}
            onClick={() => toast({ title: 'Share link copied', tone: 'success' })}>
            
            Share
          </Button>
          <Button
            size="sm"
            variant="ghost"
            icon={<DownloadIcon className="h-3.5 w-3.5" />}
            onClick={() => toast({ title: 'PDF generated', description: 'Your itinerary is downloading.', tone: 'success' })}>
            
            Download PDF
          </Button>
        </div>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {summary.map((s) =>
        <Card key={s.label} className="p-4">
            <p className="text-[12.5px] text-muted">{s.label}</p>
            <p className="mt-1 text-lg font-bold text-ink">{s.value}</p>
          </Card>
        )}
      </div>

      <Card className="overflow-hidden">
        <button
          onClick={() => setExplanationOpen((o) => !o)}
          aria-expanded={explanationOpen}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left">
          
          <span>
            <span className="flex items-center gap-2 text-[15px] font-bold text-ink">
              <SparklesIcon className="h-4 w-4 text-brand" />
              Why ATLAS recommended this
            </span>
            <span className="mt-0.5 block text-[13px] text-muted">
              Seven reasoning signals from the planner, optimizer and constraint solver.
            </span>
          </span>
          <ChevronDownIcon className={`h-4.5 w-4.5 shrink-0 text-muted transition-transform ${explanationOpen ? 'rotate-180' : ''}`} />
        </button>
        <AnimatePresence initial={false}>
          {explanationOpen &&
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-line">
            
              <ul className="grid gap-3 p-5 sm:grid-cols-2">
                {plan.reasoning.map((r) =>
              <li key={r.title} className="rounded-xl bg-canvas p-4">
                    <p className="text-[13.5px] font-semibold text-ink">{r.title}</p>
                    <p className="mt-1 text-[12.5px] leading-relaxed text-muted">{r.detail}</p>
                  </li>
              )}
              </ul>
            </motion.div>
          }
        </AnimatePresence>
      </Card>

      <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
        <div className="order-2 space-y-5 lg:order-1">
          <h2 className="text-xl font-bold text-ink">Daily itinerary</h2>
          <ItineraryTimeline days={plan.days} />
        </div>
        <div className="order-1 space-y-5 lg:order-2">
          <MapCard
            destination={plan.destination}
            stops={routeStops}
            directionsUrl={directionsUrl} />
          
          <FoodPlacesCard places={foodPlaces} destination={plan.destination} />
          <WeatherCard days={plan.weather} />
          <BudgetCard budget={plan.budget} spent={plan.estimatedCost} breakdown={plan.breakdown} />
          <CommunityInsight
            title="Community verdict"
            quote="Travellers frequently mention this area for authentic local food and calmer evenings than the main strip."
            rating={4.7}
            reviews={5240}
            positives={['Authentic local food', 'Quiet mornings', 'Short travel distances']}
            concerns={['Busy on weekends', 'Limited late-night transport']} />
          
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand/10 text-brand">
                <UsersIcon className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-[13.5px] font-semibold text-ink">{plan.travelers} travellers</p>
                <p className="text-[12.5px] text-muted">Pacing set to moderate with rest gaps</p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-success/10 text-success">
                <WalletIcon className="h-4.5 w-4.5" />
              </span>
              <div>
                <p className="text-[13.5px] font-semibold text-ink">{inr(plan.budget - plan.estimatedCost)} buffer</p>
                <p className="text-[12.5px] text-muted">Held back for shopping and extras</p>
              </div>
            </div>
          </Card>
        </div>
      </div>

      <BookingFlow
        open={bookingOpen}
        onClose={() => setBookingOpen(false)}
        item={{
          title: `${plan.destination} · Personalized Trip Package`,
          type: 'Package',
          date: plan.startDate,
          price: plan.estimatedCost,
          travelers: plan.travelers,
          image: plan.image,
          // Links the booking to the saved trip so its e-ticket can print the
          // real day-by-day itinerary and its recorded data sources.
          tripId: plan.id
        }} />
      
    </div>);

}
