import { useState } from 'react';
import { motion } from 'framer-motion';
import { ExternalLinkIcon, ImageOffIcon, MapPinIcon, SparklesIcon } from 'lucide-react';
import { DiscoverIndiaRecommendation } from '../../types';
import { cn } from '../../utils/format';

interface DiscoverIndiaCardProps {
  destination: DiscoverIndiaRecommendation;
  onClick: () => void;
  className?: string;
}

/** Maps tag strings to display-friendly pill colors. */
const TAG_COLORS: Record<string, string> = {
  culture:       'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  nature:        'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  mountains:     'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300',
  beaches:       'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-300',
  heritage:      'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-300',
  wildlife:      'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  adventure:     'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
  spiritual:     'bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300',
  food:          'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  'slow-travel': 'bg-slate-100 text-slate-700 dark:bg-slate-700/50 dark:text-slate-300',
  festival:      'bg-pink-100 text-pink-800 dark:bg-pink-900/40 dark:text-pink-300',
};

const DEFAULT_TAG_COLOR = 'bg-brand/10 text-brand';

function TagPill({ tag }: { tag: string }) {
  const color = TAG_COLORS[tag.toLowerCase()] ?? DEFAULT_TAG_COLOR;
  return (
    <span className={cn('inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize', color)}>
      {tag.replace('-', ' ')}
    </span>
  );
}

/**
 * Image placeholder shown when Wikimedia returns no photo.
 * Uses a gradient based on the destination name so each card has a distinct
 * color — never a photo of a *different* destination.
 */
function ImagePlaceholder({ name }: { name: string }) {
  // Derive a consistent hue from the name string
  const hue = name.split('').reduce((acc, ch) => acc + ch.charCodeAt(0), 0) % 360;
  const gradient = `linear-gradient(135deg, hsl(${hue}, 55%, 35%) 0%, hsl(${(hue + 40) % 360}, 45%, 55%) 100%)`;
  return (
    <div
      className="flex h-full w-full items-center justify-center"
      style={{ background: gradient }}
    >
      <ImageOffIcon className="h-8 w-8 text-white/60" />
    </div>
  );
}

export function DiscoverIndiaCard({ destination, onClick, className }: DiscoverIndiaCardProps) {
  const [imgError, setImgError] = useState(false);
  const hasImage = !!destination.image.url && !imgError;
  const displayTags = destination.tags.slice(0, 3);

  return (
    <motion.article
      id={`discover-india-card-${destination.name.toLowerCase().replace(/\s+/g, '-')}`}
      whileHover={{ y: -5 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24 }}
      className={cn(
        'group flex h-full flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-card transition-shadow hover:shadow-lift cursor-pointer',
        className
      )}
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-label={`Discover ${destination.name}, ${destination.state}`}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick(); }}
    >
      {/* ── Image ── */}
      <div className="relative h-44 overflow-hidden bg-muted/20 shrink-0">
        {hasImage ? (
          <img
            src={destination.image.url!}
            alt={`${destination.name}, ${destination.state}`}
            loading="lazy"
            onError={() => setImgError(true)}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <ImagePlaceholder name={destination.name} />
        )}

        {/* AI-curated or Popular badge */}
        <div className="absolute left-3 top-3 inline-flex items-center gap-1 rounded-full bg-brand/90 px-2.5 py-1 text-[10px] font-semibold text-white shadow backdrop-blur-sm">
          {destination.is_fallback ? (
            'Popular'
          ) : (
            <>
              <SparklesIcon className="h-3 w-3" />
              AI-curated
            </>
          )}
        </div>

        {/* Image attribution (only shown when author/license available) */}
        {hasImage && (destination.image.author || destination.image.license) && (
          <div className="absolute bottom-0 left-0 right-0 bg-black/50 px-2.5 py-1 text-[9px] text-white/80 backdrop-blur-sm truncate">
            {destination.image.source_url ? (
              <a
                href={destination.image.source_url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="inline-flex items-center gap-0.5 hover:text-white"
              >
                {[destination.image.author, destination.image.license].filter(Boolean).join(' · ')}
                <ExternalLinkIcon className="h-2.5 w-2.5 shrink-0" />
              </a>
            ) : (
              <span>{[destination.image.author, destination.image.license].filter(Boolean).join(' · ')}</span>
            )}
          </div>
        )}
      </div>

      {/* ── Content ── */}
      <div className="flex flex-1 flex-col p-4">
        {/* Name + Location */}
        <h3 className="text-[15px] font-bold text-ink leading-tight">{destination.name}</h3>
        <p className="mt-0.5 flex items-center gap-1 text-[12px] text-muted">
          <MapPinIcon className="h-3 w-3 shrink-0" />
          {destination.state}, India
        </p>

        {/* Tags */}
        {displayTags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {displayTags.map((tag) => (
              <TagPill key={tag} tag={tag} />
            ))}
          </div>
        )}

        {/* Description */}
        <p className="mt-2.5 line-clamp-2 text-[12.5px] leading-relaxed text-muted flex-1">
          {destination.description}
        </p>

        {/* Reason */}
        <div className="mt-3 border-t border-line pt-3">
          <p className="line-clamp-2 text-[11.5px] italic text-muted/80 leading-snug">
            {destination.reason}
          </p>
        </div>
      </div>
    </motion.article>
  );
}
