import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { SearchIcon, SparklesIcon } from 'lucide-react';
import { IMAGES, popularSearches } from '../../data/destinations';
import { useAtlas } from '../../contexts/AtlasContext';

export function Hero() {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  const { toast } = useAtlas();

  const search = (value: string) => {
    const term = value.trim();
    if (!term) {
      toast({ title: 'Enter a destination', description: 'Try “Goa”, “Kyoto” or “Iceland”.', tone: 'info' });
      return;
    }
    navigate(`/explore?q=${encodeURIComponent(term)}`);
  };

  return (
    <section className="mx-auto max-w-shell px-5 pt-8 lg:px-8 lg:pt-10">
      <div className="overflow-hidden rounded-3xl border border-line bg-surface shadow-card lg:rounded-4xl">
        <div className="grid items-center gap-8 lg:grid-cols-[1.05fr_1fr]">
          <div className="px-6 py-10 sm:px-10 lg:py-16 lg:pl-14">
            <motion.span
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-1.5 rounded-full bg-brand/10 px-3 py-1.5 text-[12px] font-semibold text-brand">
              
              <SparklesIcon className="h-3.5 w-3.5" />
              AI-Powered Travel Planner
            </motion.span>

            <motion.h1
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className="mt-6 font-display text-[38px] font-extrabold leading-[1.05] text-ink sm:text-5xl lg:text-[56px]">
              
              Hello, Explorer! <span aria-hidden>👋</span>
            </motion.h1>
            <motion.h2
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="mt-2 font-display text-[30px] font-bold leading-tight text-muted sm:text-4xl lg:text-[42px]">
              
              Where do you want to go?
            </motion.h2>

            <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-muted">
              Plan your perfect trip with AI recommendations, personalized itineraries and real traveler insights.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                search(query);
              }}
              className="mt-8 flex flex-col gap-3 sm:flex-row"
              role="search">
              
              <div className="relative flex-1">
                <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4.5 w-4.5 -translate-y-1/2 text-muted" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  aria-label="Search destinations, places, activities"
                  placeholder="Search destinations, places, activities..."
                  className="h-14 w-full rounded-2xl border border-line bg-surface pl-12 pr-4 text-[15px] text-ink placeholder:text-muted/80 transition-shadow focus:border-brand focus:shadow-focus focus:outline-none" />
                
              </div>
              <button
                type="submit"
                className="h-14 rounded-2xl bg-brand px-8 text-[15px] font-semibold text-white transition-transform hover:bg-blue-700 active:scale-[0.98]">
                
                Search
              </button>
            </form>

            <div className="mt-6 flex flex-wrap items-center gap-2">
              <span className="text-[13px] font-medium text-muted">Popular Searches:</span>
              {popularSearches.map((term) =>
              <button
                key={term}
                onClick={() => search(term)}
                className="rounded-full border border-line bg-canvas px-3.5 py-1.5 text-[12.5px] font-medium text-muted transition-colors hover:border-brand/40 hover:text-brand">
                
                  {term}
                </button>
              )}
            </div>
          </div>

          <div className="relative h-[300px] sm:h-[380px] lg:h-[540px]">
            <img
              src={IMAGES.heroLake}
              alt="Alpine lake with snow-capped mountains at golden hour"
              className="h-full w-full object-cover lg:rounded-l-[2.5rem]" />
            
            <div className="pointer-events-none absolute inset-y-0 left-0 hidden w-32 bg-gradient-to-r from-surface to-transparent lg:block" />
            <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-surface to-transparent lg:hidden" />
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
              className="absolute bottom-5 right-5 w-[210px] rounded-2xl border border-line bg-surface/95 p-4 shadow-lift backdrop-blur">
              
              <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-brand">Live agents</p>
              <p className="mt-1.5 text-[13px] font-semibold text-ink">9 agents ready</p>
              <p className="mt-1 text-[12px] leading-relaxed text-muted">
                Travel · Hotel · Food · Weather · Maps · Reviews
              </p>
            </motion.div>
          </div>
        </div>
      </div>
    </section>);

}
