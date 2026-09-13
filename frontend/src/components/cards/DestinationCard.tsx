import { motion } from 'framer-motion';
import { CalendarRangeIcon, HeartIcon, MapPinIcon, StarIcon } from 'lucide-react';
import { Destination } from '../../types';
import { useAtlas } from '../../contexts/AtlasContext';
import { cn, compactInr } from '../../utils/format';

export function DestinationCard({
  destination,
  variant = 'compact',
  onClick,
  className





}: {destination: Destination;variant?: 'compact' | 'detailed';onClick?: () => void;className?: string;}) {
  const { isSaved, toggleSaved } = useAtlas();
  const saved = isSaved(destination.id);

  return (
    <motion.article
      whileHover={{ y: -4 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
      className={cn(
        'group flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-card transition-shadow hover:shadow-lift',
        className
      )}>
      
      <div className="relative">
        <button
          type="button"
          onClick={onClick}
          className="block w-full text-left"
          aria-label={`View ${destination.name}`}>
          
          <div className={cn('overflow-hidden', variant === 'detailed' ? 'h-44' : 'h-40')}>
            <img
              src={destination.image}
              alt={destination.name}
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105" />
            
          </div>
        </button>
        <button
          type="button"
          onClick={() => toggleSaved(destination.id, destination.name)}
          aria-label={saved ? `Remove ${destination.name} from saved` : `Save ${destination.name}`}
          aria-pressed={saved}
          className="absolute right-3 top-3 rounded-full bg-white/90 p-2 text-slate-600 shadow-sm backdrop-blur transition-colors hover:text-danger">
          
          <HeartIcon className={cn('h-4 w-4', saved && 'fill-danger text-danger')} />
        </button>
        <div className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-slate-800 shadow-sm backdrop-blur">
          <StarIcon className="h-3 w-3 fill-warning text-warning" />
          {destination.rating}
        </div>
      </div>

      <div className="flex flex-1 flex-col p-4">
        <h3 className="text-[15px] font-bold text-ink">{destination.name}</h3>
        <p className="mt-0.5 flex items-center gap-1 text-[13px] text-muted">
          <MapPinIcon className="h-3.5 w-3.5" />
          {destination.country}
        </p>

        {variant === 'detailed' &&
        <p className="mt-2.5 line-clamp-2 text-[13px] leading-relaxed text-muted">{destination.description}</p>
        }

        <div className="mt-3 flex items-center justify-between border-t border-line pt-3 text-[12px]">
          <span className="inline-flex items-center gap-1.5 text-muted">
            <CalendarRangeIcon className="h-3.5 w-3.5" />
            {destination.durationDays} Days Trip
          </span>
          <span className="font-semibold text-brand">{compactInr(destination.budgetFrom)}</span>
        </div>

        {variant === 'detailed' &&
        <p className="mt-2 text-[12px] text-muted">Best season · {destination.bestSeason}</p>
        }
      </div>
    </motion.article>);

}
