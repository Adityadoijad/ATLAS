import { BookingInput } from './BookingFlow';
import { findDestinationByName } from '../../data/destinations';
import { AssistantPlan } from '../../types';

/**
 * Hand-off contract between a surface that has a trip ready (currently the
 * Assistant) and the existing Bookings page.
 *
 * Carried in React Router location state rather than a query string: it is
 * transient UI context, not something that belongs in a shareable URL.
 */
export const BOOKING_DRAFT_STATE_KEY = 'bookingDraft';

export interface BookingHandoffState {
  [BOOKING_DRAFT_STATE_KEY]?: unknown;
}

/** Turn a completed assistant plan into the existing BookingInput model. */
export function bookingDraftFromPlan(plan: AssistantPlan): BookingInput {
  const match = findDestinationByName(plan.destination);
  return {
    title: plan.title,
    // The whole trip is booked as one item, matching how the itinerary page's
    // "Book this trip" already works.
    type: 'Package',
    date: plan.startDate,
    price: plan.estimatedCost,
    travelers: plan.travelers,
    // Only set when the catalog actually has artwork for this destination;
    // BookingFlow renders no image rather than a broken one.
    image: match?.image
  };
}

/**
 * Validate a draft that arrived through navigation state.
 *
 * Location state is attacker- and accident-reachable (a hand-edited history
 * entry, a stale tab), so nothing is trusted: anything malformed returns null
 * and the page falls back to its normal behaviour instead of rendering a
 * broken booking or crashing.
 */
export function parseBookingDraft(value: unknown): BookingInput | null {
  if (!value || typeof value !== 'object') return null;
  const { title, type, date, price, travelers, image } = value as Partial<BookingInput>;

  if (typeof title !== 'string' || title.trim().length === 0) return null;
  if (typeof date !== 'string' || Number.isNaN(Date.parse(date))) return null;
  if (typeof price !== 'number' || !Number.isFinite(price) || price < 0) return null;
  if (typeof travelers !== 'number' || !Number.isInteger(travelers) || travelers < 1) return null;

  return {
    title: title.trim(),
    type: type ?? 'Package',
    date,
    price,
    travelers,
    image: typeof image === 'string' ? image : undefined
  };
}
