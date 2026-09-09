import { useRef } from 'react';
import type { ComponentType } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRightIcon,
  CalendarSyncIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
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
import { DestinationCard } from '../components/cards/DestinationCard';
import { SectionHeading } from '../components/ui/Primitives';
import { destinations } from '../data/destinations';
import { features } from '../data/content';

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

function RecommendedCarousel() {
  const scroller = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const scrollBy = (dir: number) => {
    scroller.current?.scrollBy({ left: dir * 320, behavior: 'smooth' });
  };

  return (
    <section className="mx-auto max-w-shell px-5 pt-16 lg:px-8">
      <SectionHeading
        title="AI Recommended for You"
        subtitle="Ranked against your saved interests, past trips and traveller reviews."
        action={
        <div className="flex items-center gap-2">
            <button
            onClick={() => scrollBy(-1)}
            aria-label="Scroll recommendations left"
            className="hidden h-9 w-9 items-center justify-center rounded-full border border-line text-muted transition-colors hover:text-ink sm:flex">
            
              <ChevronLeftIcon className="h-4 w-4" />
            </button>
            <button
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
      

      <div
        ref={scroller}
        className="no-scrollbar mt-6 flex snap-x snap-mandatory gap-5 overflow-x-auto pb-2">
        
        {destinations.slice(0, 8).map((destination) =>
        <div key={destination.id} className="w-[270px] shrink-0 snap-start">
            <DestinationCard destination={destination} onClick={() => navigate('/explore')} />
          </div>
        )}
      </div>
    </section>);

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
      <RecommendedCarousel />
      <FeatureGrid />
      <AgentFlow />
      <ClosingCta />
    </>);

}
