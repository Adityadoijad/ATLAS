import { useEffect, useRef, useState } from 'react';
import type { ComponentType } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRightIcon,
  CalendarSyncIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CompassIcon,
  LanguagesIcon,
  MessageSquareQuoteIcon,
  MicIcon,
  NetworkIcon,
  SparklesIcon,
  UserRoundCheckIcon,
  UsersIcon,
  WalletIcon } from
'lucide-react';
import { Hero } from '../components/home/Hero';
import { AgentFlow } from '../components/home/AgentFlow';
import { DiscoverIndiaCard } from '../components/home/DiscoverIndiaCard';
import { SectionHeading } from '../components/ui/Primitives';
import { features } from '../data/content';
import { fetchIndiaRecommendations } from '../services/atlasApi';
import { DiscoverIndiaRecommendation } from '../types';

const iconMap: Record<string, ComponentType<{className?: string;}>> = {
  Sparkles: SparklesIcon,
  Network: NetworkIcon,
  UserRoundCheck: UserRoundCheckIcon,
  Wallet: WalletIcon,
  MessageSquareQuote: MessageSquareQuoteIcon,
  Users: UsersIcon,
  Languages: LanguagesIcon,
  Mic: MicIcon,
  CalendarSync: CalendarSyncIcon
};

/** Skeleton card shown while recommendations are loading. */
function SkeletonCard() {
  return (
    <div className="w-[270px] shrink-0 snap-start">
      <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-card animate-pulse">
        <div className="h-44 bg-muted/20" />
        <div className="space-y-2.5 p-4">
          <div className="h-4 w-2/3 rounded bg-muted/20" />
          <div className="h-3 w-1/3 rounded bg-muted/20" />
          <div className="flex gap-1 pt-1">
            <div className="h-4 w-14 rounded-full bg-muted/20" />
            <div className="h-4 w-14 rounded-full bg-muted/20" />
          </div>
          <div className="h-3 w-full rounded bg-muted/20" />
          <div className="h-3 w-4/5 rounded bg-muted/20" />
        </div>
      </div>
    </div>
  );
}

function DiscoverIndiaSection() {
  const scroller = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const [destinations, setDestinations] = useState<DiscoverIndiaRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    fetchIndiaRecommendations()
      .then((data) => {
        if (!active) return;
        setDestinations(data);
        setLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setError(true);
        setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const scrollBy = (dir: number) => {
    scroller.current?.scrollBy({ left: dir * 300, behavior: 'smooth' });
  };

  /**
   * Navigate to the Planner with the destination pre-filled.
   * This is identical to how the Explore page and other parts of ATLAS
   * trigger the planner — PlannerPage reads location.state.destination.
   */
  const handleCardClick = (destination: DiscoverIndiaRecommendation) => {
    navigate('/plan', { state: { destination: destination.full_name } });
  };

  const isFallback = destinations.some((d) => d.is_fallback);
  const subtitleText = isFallback
    ? "Popular destinations across India. Click any card to start planning."
    : "AI-curated destinations across India, refreshed regularly. Click any card to start planning.";

  return (
    <section className="mx-auto max-w-shell px-5 pt-16 lg:px-8" aria-label="Discover India">
      <SectionHeading
        title="Discover India"
        subtitle={subtitleText}
        action={
        <div className="flex items-center gap-2">
            <button
            id="discover-india-scroll-left"
            onClick={() => scrollBy(-1)}
            aria-label="Scroll recommendations left"
            className="hidden h-9 w-9 items-center justify-center rounded-full border border-line text-muted transition-colors hover:text-ink sm:flex">
            
              <ChevronLeftIcon className="h-4 w-4" />
            </button>
            <button
            id="discover-india-scroll-right"
            onClick={() => scrollBy(1)}
            aria-label="Scroll recommendations right"
            className="hidden h-9 w-9 items-center justify-center rounded-full border border-line text-muted transition-colors hover:text-ink sm:flex">
            
              <ChevronRightIcon className="h-4 w-4" />
            </button>
            <Link to="/explore" className="text-[13px] font-semibold text-brand hover:underline">
              View all
            </Link>
          </div>
        } />
      

      {/* Loading state */}
      {loading && (
        <div className="mt-2 mb-1 flex items-center gap-2 text-[12.5px] text-muted">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
          >
            <SparklesIcon className="h-3.5 w-3.5" />
          </motion.div>
          Discovering places for you…
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="mt-6 flex items-center gap-3 rounded-2xl border border-line bg-surface p-4 text-[13px] text-muted">
          <CompassIcon className="h-5 w-5 shrink-0 text-muted" />
          <span>Recommendations are temporarily unavailable. <Link to="/explore" className="text-brand hover:underline">Browse all destinations →</Link></span>
        </div>
      )}

      {/* Destination cards */}
      <div
        ref={scroller}
        className="no-scrollbar mt-6 flex snap-x snap-mandatory gap-5 overflow-x-auto pb-2"
        id="discover-india-carousel"
      >
        {loading
          ? Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
          : destinations.map((dest) => (
              <div key={dest.full_name} className="w-[270px] shrink-0 snap-start">
                <DiscoverIndiaCard
                  destination={dest}
                  onClick={() => handleCardClick(dest)}
                />
              </div>
            ))
        }
      </div>
    </section>
  );

}



function FeatureGrid() {
  return (
    <section className="mx-auto max-w-shell px-5 pt-20 lg:px-8">
      <SectionHeading
        title="Intelligence built for real trips"
        subtitle="Nine capabilities that turn a rough idea into a plan you can actually follow." />
      
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((feature, index) => {
          const Icon = iconMap[feature.icon] ?? SparklesIcon;
          return (
            <motion.article
              key={feature.title}
              initial={{ opacity: 0, y: 14 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.3, delay: index % 3 * 0.05 }}
              className="rounded-2xl border border-line bg-surface p-6 transition-shadow hover:shadow-card">
              
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand/10 text-brand">
                <Icon className="h-5 w-5" />
              </span>
              <h3 className="mt-4 text-[15px] font-bold text-ink">{feature.title}</h3>
              <p className="mt-1.5 text-[13.5px] leading-relaxed text-muted">{feature.description}</p>
            </motion.article>);

        })}
      </div>
    </section>);

}

function ClosingCta() {
  return (
    <section className="mx-auto max-w-shell px-5 pb-20 lg:px-8">
      <div className="flex flex-col items-start justify-between gap-6 rounded-3xl bg-brand px-8 py-12 text-white sm:flex-row sm:items-center lg:px-14">
        <div>
          <h2 className="font-display text-3xl font-bold sm:text-[34px]">Ready to plan your next trip?</h2>
          <p className="mt-2 max-w-xl text-[15px] text-white/80">
            Tell ATLAS where you want to go, and the agents handle transport, stays, food, weather and budget together.
          </p>
        </div>
        <Link
          to="/plan"
          className="inline-flex h-13 items-center gap-2 rounded-xl bg-white px-7 text-[15px] font-semibold text-brand transition-transform hover:scale-[1.02]">
          
          Plan a New Trip
          <ArrowRightIcon className="h-4 w-4" />
        </Link>
      </div>
    </section>);

}

export function HomePage() {
  return (
    <>
      <Hero />
      <DiscoverIndiaSection />
      <FeatureGrid />
      <AgentFlow />
      <ClosingCta />
    </>);

}
