import React from 'react';
import { motion } from 'framer-motion';
import {
  BedDoubleIcon,
  ClockIcon,
  ExternalLinkIcon,
  MapIcon,
  MapPinIcon,
  NavigationIcon,
  PlaneIcon,
  StarIcon,
  TicketIcon,
  UtensilsIcon } from
'lucide-react';
import { ItineraryDay, ItineraryItem } from '../../types';
import { Card } from '../ui/Primitives';
import { cn, formatDate, inr } from '../../utils/format';

const kindIcon: Record<ItineraryItem['kind'], React.ComponentType<{className?: string;}>> = {
  travel: PlaneIcon,
  stay: BedDoubleIcon,
  food: UtensilsIcon,
  activity: TicketIcon
};

export function ItineraryTimeline({ days }: {days: ItineraryDay[];}) {
  return (
    <div className="space-y-6">
      {days.map((day) =>
      <Card key={day.day} className="overflow-hidden">
          <div className="flex items-baseline justify-between border-b border-line bg-canvas/60 px-5 py-4">
            <h3 className="text-[15px] font-bold text-ink">
              Day {day.day} — {day.title}
            </h3>
            <span className="text-[12.5px] text-muted">{formatDate(day.date)}</span>
          </div>
          <ol className="px-5 py-4">
            {day.items.map((item, index) => {
            const Icon = kindIcon[item.kind];
            return (
              <motion.li
                key={`${day.day}-${item.time}-${index}`}
                initial={{ opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.25, delay: index * 0.03 }}
                className="relative flex gap-4 pb-6 last:pb-0">
                
                  {index < day.items.length - 1 &&
                <span className="absolute left-[19px] top-10 h-[calc(100%-1.5rem)] w-px bg-line" aria-hidden />
                }
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand/10 text-brand">
                    <Icon className="h-4.5 w-4.5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-3">
                      <span className="font-mono text-[12.5px] font-semibold text-brand">{item.time}</span>
                      <h4 className="text-[14.5px] font-semibold text-ink">{item.title}</h4>
                    </div>
                    <p className="mt-0.5 flex items-center gap-1 text-[13px] text-muted">
                      <MapPinIcon className="h-3.5 w-3.5" /> {item.location}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[12.5px] text-muted">
                      <span className="inline-flex items-center gap-1">
                        <ClockIcon className="h-3.5 w-3.5" /> {item.duration}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <StarIcon className="h-3.5 w-3.5 fill-warning text-warning" /> {item.rating}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <NavigationIcon className="h-3.5 w-3.5" /> {item.distanceKm} km
                      </span>
                      <span className={cn('font-semibold', item.cost === 0 ? 'text-success' : 'text-ink')}>
                        {item.cost === 0 ? 'Free' : inr(item.cost)}
                      </span>
                    </div>
                  </div>
                </motion.li>);

          })}
          </ol>
        </Card>
      )}
    </div>);

}

export function MapCard({
  destination,
  stops,
  directionsUrl




}: {destination: string;stops: string[];directionsUrl?: string | null;}) {
  return (
    <Card className="overflow-hidden">
      <div className="relative h-56 bg-[#e8eef7] dark:bg-[#16233a]">
        <svg viewBox="0 0 320 220" className="h-full w-full" role="img" aria-label={`Route map for ${destination}`}>
          <rect width="320" height="220" fill="currentColor" className="text-[#dde6f3] dark:text-[#132038]" />
          {[40, 80, 120, 160, 200].map((y) =>
          <line key={y} x1="0" y1={y} x2="320" y2={y} stroke="#ffffff" strokeOpacity="0.5" strokeWidth="1" />
          )}
          {[60, 120, 180, 240].map((x) =>
          <line key={x} x1={x} y1="0" x2={x} y2="220" stroke="#ffffff" strokeOpacity="0.5" strokeWidth="1" />
          )}
          <path d="M40 180 C 90 150, 110 90, 160 90 S 250 60, 285 40" fill="none" stroke="#2563EB" strokeWidth="3" strokeDasharray="7 6" strokeLinecap="round" />
          {[
          [40, 180],
          [160, 90],
          [285, 40]].
          map(([cx, cy], i) =>
          <g key={i}>
              <circle cx={cx} cy={cy} r="9" fill="#2563EB" fillOpacity="0.18" />
              <circle cx={cx} cy={cy} r="4.5" fill="#2563EB" />
            </g>
          )}
        </svg>
        <span className="absolute left-4 top-4 inline-flex items-center gap-1.5 rounded-full bg-white/90 px-3 py-1.5 text-[12px] font-semibold text-slate-800 shadow-sm">
          <MapIcon className="h-3.5 w-3.5" /> {destination} route
        </span>
      </div>
      <div className="p-5">
        <p className="text-[13px] font-semibold text-ink">Optimised by the Maps Agent</p>
        <ul className="mt-3 space-y-2">
          {stops.map((stop, i) =>
          <li key={stop} className="flex items-start gap-2.5 text-[13px] text-muted">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand/10 text-[11px] font-bold text-brand">
                {i + 1}
              </span>
              {stop}
            </li>
          )}
        </ul>
        {/* External hand-off, not a replacement for the route above. Rendered
            only when there are at least two mappable stops, so the link can
            never open a broken map. */}
        {directionsUrl &&
        <a
          href={directionsUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Open this ${destination} route in Google Maps (opens in a new tab)`}
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-line bg-canvas px-3 py-2.5 text-[13px] font-semibold text-brand transition-colors hover:border-brand/40 hover:bg-brand/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand">

            <MapIcon className="h-4 w-4" />
            Open Route in Google Maps
            <ExternalLinkIcon className="h-3.5 w-3.5" />
          </a>
        }
      </div>
    </Card>);

}