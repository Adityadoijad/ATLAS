/**
 * Mock service layer for ATLAS.
 *
 * Every function here mimics a future FastAPI endpoint (path noted in the comment).
 * UI code must only ever talk to this module — swapping these bodies for `fetch`
 * calls is the only change required to connect the real backend.
 */
import { findDestination } from '../data/destinations';
import {
  AssistantPlan,
  Booking,
  ChatMessage,
  DiscoverIndiaRecommendation,
  ItineraryItem,
  DestinationDetails,
  DestinationForecast,
  LocationSuggestion,
  TripRoute,
  LostFoundItem,
  DiscoveredDestination,
  PlannerPreferences,
  RealPlace,
  RecommendedDestination,
  SavedPlace,
  TripPlan,
  Trip } from
'../types';

import { bookingReference, timeNow, uid } from '../utils/format';

const latency = (ms = 320) => new Promise((resolve) => setTimeout(resolve, ms));

const ACTIVITY_CATEGORIES = ['accommodation', 'travel', 'food', 'activity'] as const;
type ActivityCategory = (typeof ACTIVITY_CATEGORIES)[number];

function isActivityCategory(value: string | undefined): value is ActivityCategory {
  return !!value && (ACTIVITY_CATEGORIES as readonly string[]).includes(value);
}

const CATEGORY_TO_KIND: Record<ActivityCategory, ItineraryItem['kind']> = {
  accommodation: 'stay',
  travel: 'travel',
  food: 'food',
  activity: 'activity'
};

const apiUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

async function apiRequest<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers
    }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export async function registerUser(input: { name: string; email: string; password: string }): Promise<AuthUser> {
  return apiRequest<AuthUser>('/api/auth/register', { method: 'POST', body: JSON.stringify(input) });
}

export async function loginUser(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
  const body = new URLSearchParams({ username: email, password });
  return apiRequest('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body
  });
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  return apiRequest<AuthUser>('/api/auth/me', {}, token);
}

export function getGoogleAuthUrl(): string {
  return `${apiUrl}/api/auth/google`;
}

export async function fetchPersistedTrips(token: string): Promise<Trip[]> {
  const data = await apiRequest<Array<Record<string, unknown>>>('/api/trips', {}, token);
  return data.map((trip) => ({
    id: String(trip.id),
    destination: String(trip.destination),
    country: '',
    // Resolved per destination by the caller; never another place's photo.
    image: '',
    startDate: String(trip.start_date),
    endDate: String(trip.end_date),
    travelers: Number(trip.travelers),
    budget: Number(trip.budget ?? 0),
    status: trip.status === 'past' ? 'past' : 'upcoming',
    createdAt: trip.created_at ? String(trip.created_at) : undefined
  }));
}

/**
 * The user's most recently created saved trip, as a full plan.
 *
 * Lets the itinerary page survive a refresh by restoring what the traveller
 * actually planned. Returns null when they have no saved trip yet, so the
 * caller can show an empty state instead of inventing a placeholder trip for
 * a destination they never asked for.
 */
export async function fetchLatestTripPlan(token: string): Promise<TripPlan | null> {
  const data = await apiRequest<Array<GeneratedTripResponse & {created_at?: string;}>>('/api/trips', {}, token);
  const [latest] = data.
  filter((trip) => (trip.itinerary_days ?? []).length > 0).
  sort((a, b) => String(b.created_at ?? '').localeCompare(String(a.created_at ?? '')));
  return latest ? mapGeneratedTrip(latest, latest.budget ?? 0) : null;
}

/**
 * GET /api/trips/{id} — one saved trip, as a full plan.
 *
 * Returns null when the trip does not exist or is not the caller's, so the
 * itinerary page shows its empty state instead of a stand-in trip. Ownership
 * is enforced server-side; this never trusts an id from the URL.
 */
export async function fetchTripPlanById(tripId: string, token: string): Promise<TripPlan | null> {
  try {
    const trip = await apiRequest<GeneratedTripResponse>(`/api/trips/${tripId}`, {}, token);
    return mapGeneratedTrip(trip, trip.budget ?? 0);
  } catch {
    return null;
  }
}

export async function fetchPersistedSavedPlaces(token: string): Promise<SavedPlace[]> {
  const data = await apiRequest<Array<Record<string, unknown>>>('/api/saved-places', {}, token);
  return data.map((place) => ({
    id: String(place.place_id),
    name: String(place.name),
    subtitle: String(place.description ?? ''),
    image: String(place.image_url ?? ''),
    kind: (String(place.category ?? place.type) as SavedPlace['kind']),
    rating: Number(place.rating ?? 0)
  }));
}

/** snake_case wire fields -> the camelCase RealPlace the UI renders. */
function mapRealPlace(place: {
  name: string;category: string | null;cuisine: string | null;rating: number | null;
  address: string | null;phone: string | null;website: string | null;opening_hours: string | null;
  latitude: number | null;longitude: number | null;source: string;
}): RealPlace {
  return {
    name: place.name,
    category: place.category,
    cuisine: place.cuisine,
    rating: place.rating,
    address: place.address,
    phone: place.phone,
    website: place.website,
    openingHours: place.opening_hours,
    latitude: place.latitude,
    longitude: place.longitude,
    source: place.source
  };
}

export async function fetchDestinationDetails(destinationName: string, token: string): Promise<DestinationDetails> {
  const data = await apiRequest<{
    destination: string;
    is_realtime_location: boolean;
    latitude: number | null;
    longitude: number | null;
    weather: {
      is_realtime_data: boolean;
      temperature_c: number | null;
      feels_like_c: number | null;
      humidity_percent: number | null;
      wind_speed_ms: number | null;
      condition: string | null;
      icon: string | null;
      forecast: Array<{ timestamp: string; weekday: string | null; temperature_c: number; condition: string; icon: string | null }>;
      unavailable_reason: string | null;
    };
    activities: Array<{ name: string; category: string | null; cuisine: string | null; rating: number | null; address: string | null; phone: string | null; website: string | null; opening_hours: string | null; latitude: number | null; longitude: number | null; source: string }>;
    activities_unavailable_reason: string | null;
    restaurants: Array<{ name: string; category: string | null; cuisine: string | null; rating: number | null; address: string | null; phone: string | null; website: string | null; opening_hours: string | null; latitude: number | null; longitude: number | null; source: string }>;
    restaurants_unavailable_reason: string | null;
  }>(`/api/destinations/${encodeURIComponent(destinationName)}/details`, {}, token);

  return {
    destination: data.destination,
    isRealtimeLocation: data.is_realtime_location,
    latitude: data.latitude,
    longitude: data.longitude,
    weather: {
      isRealtimeData: data.weather.is_realtime_data,
      temperatureC: data.weather.temperature_c,
      feelsLikeC: data.weather.feels_like_c,
      humidityPercent: data.weather.humidity_percent,
      windSpeedMs: data.weather.wind_speed_ms,
      condition: data.weather.condition,
      icon: data.weather.icon,
      forecast: data.weather.forecast.map((f) => ({
        timestamp: f.timestamp,
        weekday: f.weekday,
        temperatureC: f.temperature_c,
        condition: f.condition,
        icon: f.icon
      })),
      unavailableReason: data.weather.unavailable_reason
    },
    activities: data.activities.map(mapRealPlace),
    activitiesUnavailableReason: data.activities_unavailable_reason,
    restaurants: data.restaurants.map(mapRealPlace),
    restaurantsUnavailableReason: data.restaurants_unavailable_reason
  };
}

/**
 * GET /api/weather/forecast — the only way the frontend gets weather.
 *
 * The OpenWeatherMap key lives in backend configuration and never reaches the
 * browser, so there is no direct-to-provider path here to fall back on.
 *
 * A provider failure comes back as a 200 with `is_realtime_data: false`, which
 * is why this resolves rather than throwing: "weather is unavailable" is a
 * result the UI renders, not an error it recovers from.
 */
export async function fetchDestinationForecast(
  destination: string,
  token: string
): Promise<DestinationForecast> {
  const data = await apiRequest<{
    destination: string;
    is_realtime_data: boolean;
    resolved_destination: string | null;
    latitude: number | null;
    longitude: number | null;
    local_date: string | null;
    forecast_through: string | null;
    days: Array<{
      date: string;
      weekday: string;
      temperature_c: number;
      temperature_min_c: number;
      temperature_max_c: number;
      condition: string | null;
      icon: string | null;
      step_count: number;
      local_time_of_summary: string;
    }>;
    unavailable_reason: string | null;
  }>(`/api/weather/forecast?destination=${encodeURIComponent(destination)}`, {}, token);

  return {
    destination: data.destination,
    isRealtimeData: data.is_realtime_data,
    resolvedDestination: data.resolved_destination,
    latitude: data.latitude,
    longitude: data.longitude,
    localDate: data.local_date,
    forecastThrough: data.forecast_through,
    days: data.days.map((day) => ({
      date: day.date,
      weekday: day.weekday,
      temperatureC: day.temperature_c,
      temperatureMinC: day.temperature_min_c,
      temperatureMaxC: day.temperature_max_c,
      condition: day.condition,
      icon: day.icon,
      stepCount: day.step_count,
      localTimeOfSummary: day.local_time_of_summary
    })),
    unavailableReason: data.unavailable_reason
  };
}

/**
 * GET /api/destinations/:name/photo — a real photograph of a place.
 *
 * Returns null when Wikimedia has no genuine photo of it. The caller then
 * draws a neutral placeholder: substituting a picture of a *different*
 * destination is the bug this replaced, where a Manali trip rendered a Goa
 * beach because Goa was the universal fallback image.
 */
export async function fetchDestinationPhoto(destination: string): Promise<string | null> {
  const data = await apiRequest<{ url: string | null }>(
    `/api/destinations/${encodeURIComponent(destination)}/photo`
  );
  return data.url;
}

export async function fetchRecommendations(token: string): Promise<RecommendedDestination[]> {
  const data = await apiRequest<Array<{ destination_id: string; score: number; reason: string }>>(
    '/api/recommendations',
    {},
    token
  );
  return data.
  map((item) => {
    const destination = findDestination(item.destination_id);
    return destination ? { ...destination, reason: item.reason } : null;
  }).
  filter((item): item is RecommendedDestination => item !== null);
}

export async function discoverDestinations(token: string): Promise<DiscoveredDestination[]> {
  const data = await apiRequest<Array<{
    name: string;
    country: string;
    description: string;
    categories: string[];
    estimated_budget_inr: number;
    best_season: string;
    duration_days: number;
    image_url: string | null;
  }>>('/api/recommendations/discover', { method: 'POST' }, token);
  return data.map((item) => ({
    name: item.name,
    country: item.country,
    description: item.description,
    categories: item.categories,
    budgetFrom: item.estimated_budget_inr,
    bestSeason: item.best_season,
    durationDays: item.duration_days,
    // Left undefined rather than defaulted to a bundled image: a stored photo
    // of a different place would misrepresent the suggestion.
    imageUrl: item.image_url ?? undefined
  }));
}

/**
 * GET /api/destinations/recommendations — public, no auth token required.
 *
 * Returns AI-curated India destinations dynamically generated by Groq,
 * validated by Nominatim, and illustrated with Wikimedia photos. The backend
 * caches results for 6-10 h so this is fast after the first call.
 *
 * Returns an empty array on any error — the home page must always render.
 */
export async function fetchIndiaRecommendations(): Promise<DiscoverIndiaRecommendation[]> {
  try {
    const data = await apiRequest<Array<{
      name: string;
      state: string;
      country: string;
      full_name: string;
      description: string;
      reason: string;
      tags: string[];
      latitude: number;
      longitude: number;
      image: {
        url: string | null;
        source: string | null;
        source_url: string | null;
        author: string | null;
        license: string | null;
      };
      is_fallback?: boolean;
    }>>('/api/destinations/recommendations', { method: 'GET' });

    return data.map((item) => ({
      name: item.name,
      state: item.state,
      country: item.country,
      full_name: item.full_name,
      description: item.description,
      reason: item.reason,
      tags: item.tags,
      latitude: item.latitude,
      longitude: item.longitude,
      image: {
        url: item.image?.url ?? null,
        source: item.image?.source ?? null,
        source_url: item.image?.source_url ?? null,
        author: item.image?.author ?? null,
        license: item.image?.license ?? null,
      },
      // Carried through so the UI can say these are the curated stand-ins
      // rather than live AI picks. Previously dropped here, which silently
      // disabled the fallback notice on every page that checks it.
      is_fallback: item.is_fallback ?? false,
    }));
  } catch {
    // Never propagate: the home page must always render even if this fails.
    return [];
  }
}

export async function deletePersistedTrip(id: string, token: string): Promise<void> {
  await apiRequest<void>(`/api/trips/${id}`, { method: 'DELETE' }, token);
}

export async function deletePersistedSavedPlace(id: string, token: string): Promise<void> {
  await apiRequest<void>(`/api/saved-places/${encodeURIComponent(id)}`, { method: 'DELETE' }, token);
}

export async function savePersistedPlace(
  place: { place_id: string; name: string; type: string; category?: string },
  token: string
): Promise<void> {
  await apiRequest<void>('/api/saved-places', { method: 'POST', body: JSON.stringify(place) }, token);
}

export async function persistTripPlan(plan: TripPlan, token: string): Promise<string> {
  const trip = await apiRequest<{ id: string }>('/api/trips', {
    method: 'POST',
    body: JSON.stringify({
      title: `Trip to ${plan.destination}`,
      destination: plan.destination,
      start_date: plan.startDate,
      end_date: plan.endDate,
      travelers: plan.travelers,
      budget: plan.budget,
      preferences: {},
      currency: 'INR',
      status: 'upcoming'
    })
  }, token);
  for (const day of plan.days) {
    await apiRequest(`/api/trips/${trip.id}/itinerary`, {
      method: 'POST',
      body: JSON.stringify({
        day_number: day.day,
        date: day.date,
        title: day.title,
        description: day.items.map((item) => `${item.time} ${item.title} — ${item.location}`).join('\n'),
        estimated_cost: day.items.reduce((total, item) => total + item.cost, 0)
      })
    }, token);
  }
  return trip.id;
}

/** POST /bookings */
export async function createBooking(input: {
  title: string;
  type: Booking['type'];
  date: string;
  price: number;
  travelers: number;
  image?: string;
  tripId?: string;
  leadTravelerName?: string;
  leadTravelerEmail?: string;
  leadTravelerPhone?: string;
  idDocumentType?: string;
}): Promise<Booking> {
  const token = localStorage.getItem('atlas_access_token');

  // Signed in: the booking is persisted so it keeps a stable reference and can
  // issue an e-ticket later. Signed out, it stays the local demo booking it
  // has always been — with no id, so no ticket is offered for it.
  if (token) {
    const created = await apiRequest<{
      id: string;
      reference: string;
      title: string;
      booking_type: string;
      travel_date: string;
      price: number;
      travelers: number;
      status: string;
    }>(
      '/api/bookings',
      {
        method: 'POST',
        body: JSON.stringify({
          title: input.title,
          booking_type: input.type,
          travel_date: input.date,
          price: input.price,
          travelers: input.travelers,
          trip_id: input.tripId ?? null,
          lead_traveler_name: input.leadTravelerName ?? null,
          lead_traveler_email: input.leadTravelerEmail ?? null,
          lead_traveler_phone: input.leadTravelerPhone ?? null,
          id_document_type: input.idDocumentType ?? null
        })
      },
      token
    );
    return {
      id: created.id,
      reference: created.reference,
      title: created.title,
      type: created.booking_type as Booking['type'],
      image: input.image ?? '',
      date: created.travel_date,
      price: created.price,
      travelers: created.travelers,
      status: created.status as Booking['status'],
      persisted: true
    };
  }

  await latency(900);
  return {
    id: uid('bk'),
    reference: bookingReference(),
    title: input.title,
    type: input.type,
    image: input.image ?? '',
    date: input.date,
    price: input.price,
    travelers: input.travelers,
    status: 'upcoming'
  };
}

/** GET /api/bookings — the signed-in user's persisted bookings. */
export async function fetchPersistedBookings(token: string): Promise<Booking[]> {
  const data = await apiRequest<Array<{
    id: string;reference: string;title: string;booking_type: string;
    travel_date: string;price: number;travelers: number;status: string;created_at: string;
  }>>('/api/bookings', {}, token);
  return data.map((booking) => ({
    id: booking.id,
    reference: booking.reference,
    title: booking.title,
    type: booking.booking_type as Booking['type'],
    image: '',
    date: booking.travel_date,
    price: booking.price,
    travelers: booking.travelers,
    status: booking.status as Booking['status'],
    createdAt: booking.created_at,
    persisted: true
  }));
}

export async function cancelPersistedBooking(id: string, token: string): Promise<void> {
  await apiRequest(`/api/bookings/${id}/cancel`, { method: 'POST' }, token);
}

/**
 * Download a booking's e-ticket PDF.
 *
 * Fetched rather than linked because the endpoint is private and needs the
 * Authorization header; the response becomes a blob the browser saves. The
 * filename comes from the server's Content-Disposition so the document and
 * its name always agree.
 */
/** GET /api/bookings/email-capability — is outbound email configured at all? */
export async function fetchEmailCapability(token: string): Promise<boolean> {
  try {
    const data = await apiRequest<{available: boolean;}>('/api/bookings/email-capability', {}, token);
    return data.available === true;
  } catch {
    // Treat an unreachable capability check as "not available": better to hide
    // the action than to offer one that cannot work.
    return false;
  }
}

export interface BookingEmailResult {
  recipient: string;
  attachmentFilename: string;
}

/**
 * POST /api/bookings/{id}/confirmation-email
 *
 * Emails the e-ticket to the account's own registered address — no recipient
 * is sent from here. A rejection means the *email* failed; the booking is
 * untouched, which is why the caller reports the two states separately.
 */
export async function emailBookingConfirmation(bookingId: string, token: string): Promise<BookingEmailResult> {
  const data = await apiRequest<{
    status: string;recipient: string;attachment_filename: string;
  }>(`/api/bookings/${bookingId}/confirmation-email`, { method: 'POST' }, token);
  return { recipient: data.recipient, attachmentFilename: data.attachment_filename };
}

export async function downloadBookingTicket(bookingId: string, token: string): Promise<void> {
  const response = await fetch(`${apiUrl}/api/bookings/${bookingId}/ticket`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(
      typeof detail?.detail === 'string' ? detail.detail : `Could not generate the ticket (${response.status}).`
    );
  }

  const disposition = response.headers.get('Content-Disposition') ?? '';
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = url;
    link.download = match?.[1] ?? `ATLAS-E-Ticket-${bookingId}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    // Release the blob once the browser has taken the download.
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}

/** POST /assistant/message  → POST /api/chat (FastAPI + Groq) */
interface GeneratedItineraryDay {
  day_number: number;
  date: string;
  title: string;
  description: string | null;
}

interface GeneratedTripResponse {
  id: string;
  boarding_location?: {
    name: string;
    display_name: string | null;
    latitude: number | null;
    longitude: number | null;
  } | null;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  travelers: number;
  budget: number | null;
  itinerary_days: GeneratedItineraryDay[];
  data_context?: Record<string, unknown>;
}

function mapGeneratedTrip(response: GeneratedTripResponse, fallbackBudget: number): TripPlan {
  const budget = response.budget ?? fallbackBudget;
  const days = response.itinerary_days.map((day) => {
    const activities = (day.description ?? '').split('\n').filter(Boolean).map((line) => {
      const [time = '09:00', description = 'Planned activity', location = response.destination, cost = '0', category] =
        line.split(' | ');
      return {
        time,
        description,
        location,
        estimated_cost: Number(cost) || 0,
        // Supplied by the backend (strict enum). Trips saved before the
        // category field existed have only 4 fields, so fall back to
        // 'activity' rather than guessing from the description text.
        category: (isActivityCategory(category) ? category : 'activity') as ActivityCategory
      };
    });
    return {
      day_number: day.day_number,
      day: day.day_number,
      date: day.date,
      title: day.title,
      activities,
      items: activities.map((activity) => ({
        time: activity.time,
        title: activity.description,
        location: activity.location,
        duration: 'Flexible',
        cost: activity.estimated_cost,
        kind: CATEGORY_TO_KIND[activity.category]
      }))
    };
  });

  const sumByCategory = (category: ActivityCategory) =>
  days.reduce(
    (total, day) =>
    total +
    day.activities.
    filter((activity) => activity.category === category).
    reduce((sum, activity) => sum + activity.estimated_cost, 0),
    0
  );

  return {
    id: response.id,
    title: response.title,
    destination: response.destination,
    country: '',
    // Resolved per destination by DestinationImage; never another place's photo.
    image: '',
    startDate: response.start_date,
    endDate: response.end_date,
    start_date: response.start_date,
    end_date: response.end_date,
    travelers: response.travelers,
    budget,
    estimatedCost: days.reduce((total, day) => total + day.items.reduce((sum, item) => sum + item.cost, 0), 0),
    // Every cost lands in exactly one bucket, so the four rows sum to
    // estimatedCost — no double counting and nothing invented locally.
    breakdown: [
      { label: 'Accommodation', value: sumByCategory('accommodation') },
      { label: 'Travel', value: sumByCategory('travel') },
      { label: 'Food', value: sumByCategory('food') },
      { label: 'Activities', value: sumByCategory('activity') }
    ],
    days,
    reasoning: [{ title: 'Generated by ATLAS', detail: 'This itinerary was generated and saved to your account.' }],
    is_realtime_data: response.data_context?.is_realtime_data === false ? false : undefined,
    data_context: response.data_context,
    boardingLocation: response.boarding_location
      ? {
          name: response.boarding_location.name,
          displayName: response.boarding_location.display_name,
          latitude: response.boarding_location.latitude,
          longitude: response.boarding_location.longitude
        }
      : null
  };
}

/**
 * GET /api/trips/:id/route — the trip's canonical ordered stops and real legs.
 *
 * Fetched separately from the itinerary because geocoding runs at one request
 * per second: the timeline renders immediately and travel metadata fills in.
 *
 * Routing failures arrive as a 200 with `routing_available: false` on each
 * leg, so the caller shows an explicit unavailable state — never 0 km.
 */
export async function fetchTripRoute(tripId: string, token: string): Promise<TripRoute> {
  const data = await apiRequest<{
    trip_id: string;
    stops: Array<{
      index: number; label: string; query: string;
      latitude: number | null; longitude: number | null;
      is_boarding: boolean; resolved: boolean;
    }>;
    legs: Array<{
      from_index: number; to_index: number;
      distance_km: number | null; duration_minutes: number | null;
      routing_available: boolean;
    }>;
    unavailable_reason: string | null;
  }>(`/api/trips/${encodeURIComponent(tripId)}/route`, {}, token);

  return {
    tripId: data.trip_id,
    stops: data.stops.map((stop) => ({
      index: stop.index,
      label: stop.label,
      query: stop.query,
      latitude: stop.latitude,
      longitude: stop.longitude,
      isBoarding: stop.is_boarding,
      resolved: stop.resolved
    })),
    legs: data.legs.map((leg) => ({
      fromIndex: leg.from_index,
      toIndex: leg.to_index,
      distanceKm: leg.distance_km,
      durationMinutes: leg.duration_minutes,
      routingAvailable: leg.routing_available
    })),
    unavailableReason: data.unavailable_reason
  };
}

/**
 * GET /api/locations/search — place suggestions for the boarding-location field.
 *
 * Goes through ATLAS rather than straight to Nominatim so one User-Agent and
 * one rate limiter sit in front of the geocoder, as its usage policy requires.
 */
export async function searchLocations(query: string, token: string): Promise<LocationSuggestion[]> {
  const data = await apiRequest<{
    results: Array<{ name: string; display_name: string; latitude: number; longitude: number }>;
    unavailable_reason: string | null;
  }>(`/api/locations/search?q=${encodeURIComponent(query)}`, {}, token);

  return data.results.map((item) => ({
    name: item.name,
    displayName: item.display_name,
    latitude: item.latitude,
    longitude: item.longitude
  }));
}

/**
 * POST /api/trips/generate.
 *
 * Requires a signed-in account. The previous signed-out branch returned a
 * fabricated itinerary — invented stops, costs and travel-time claims — with
 * no provenance flag, so it rendered identically to a real AI plan.
 */
export async function generateTripPlan(prefs: PlannerPreferences): Promise<TripPlan> {
  const token = localStorage.getItem('atlas_access_token');
  if (!token) {
    throw new Error('Sign in to generate a trip. ATLAS saves your itinerary to your account.');
  }

  const response = await apiRequest<GeneratedTripResponse>('/api/trips/generate', {
    method: 'POST',
    body: JSON.stringify({
      destination: prefs.destination,
      start_date: prefs.startDate,
      end_date: prefs.endDate,
      budget: prefs.budget,
      travelers: Math.max(1, prefs.adults + prefs.children),
      // The backend re-geocodes this by name rather than trusting coordinates
      // from the browser, and rejects the trip if it cannot place it.
      boarding_location: prefs.boardingLocation
        ? {
            name: prefs.boardingLocation.name,
            latitude: prefs.boardingLocation.latitude,
            longitude: prefs.boardingLocation.longitude,
            display_name: prefs.boardingLocation.displayName
          }
        : null,
      preferences: {
        interests: prefs.interests,
        transport: prefs.transport,
        accommodation: prefs.accommodation,
        food: prefs.food,
        accessibility: prefs.accessibility,
        notes: prefs.notes
      },
      currency: prefs.currency
    })
  }, token);
  return mapGeneratedTrip(response, prefs.budget);
}

export async function sendAssistantMessage(text: string): Promise<ChatMessage> {
  // Base URL from Vite env variable; falls back to localhost:8000 for safety.
  const apiUrl = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';
  const endpoint = `${apiUrl}/api/chat`;

  let responseText: string;
  // Only set when the backend says this reply completed a full itinerary.
  let plan: AssistantPlan | undefined;

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
      // Abort after 60 s so the UI never hangs indefinitely
      signal: AbortSignal.timeout(60_000),
    });

    if (!res.ok) {
      // Try to surface a meaningful message from the backend if available
      let detail = `Server responded with status ${res.status}.`;
      try {
        const errorBody = await res.json();
        if (errorBody?.detail) detail = String(errorBody.detail);
      } catch {
        // ignore JSON parse errors — use the default message
      }
      responseText = `Sorry, I ran into a problem: ${detail} Please try again in a moment.`;
    } else {
      const data = await res.json();
      if (typeof data?.response === 'string' && data.response.trim()) {
        responseText = data.response;
        if (data.plan) {
          plan = {
            title: String(data.plan.title),
            destination: String(data.plan.destination),
            startDate: String(data.plan.start_date),
            endDate: String(data.plan.end_date),
            travelers: Number(data.plan.travelers),
            estimatedCost: Number(data.plan.estimated_cost),
            currency: String(data.plan.currency ?? 'INR')
          };
        }
      } else {
        responseText = 'I received an unexpected response. Please try again.';
      }
    }
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'TimeoutError') {
      responseText = 'The request timed out. The AI is taking longer than usual — please try again.';
    } else if (err instanceof TypeError) {
      // fetch throws TypeError on network failure / CORS / no server
      responseText =
        'Could not reach the ATLAS server. Make sure the backend is running on http://localhost:8000.';
    } else {
      responseText = 'An unexpected error occurred. Please try again.';
    }
  }

  return {
    id: uid('m'),
    role: 'assistant',
    content: responseText,
    time: timeNow(),
    plan,
  };
}


/** POST /lost-found */
/** Maps a persisted report onto the shape the board already renders. */
function mapLostFound(report: {
  id: string;title: string;report_type: 'lost' | 'found';category: string;location: string;
  reported_date: string;description: string;image_url: string | null;contact: string;status: string;
}): LostFoundItem {
  return {
    id: report.id,
    title: report.title,
    type: report.report_type,
    category: report.category,
    location: report.location,
    date: report.reported_date,
    description: report.description,
    // Photos are served from the backend, so prefix the stored path.
    image: report.image_url ? `${apiUrl}${report.image_url}` : '',
    // A traveller's own photo of their own item — never a stand-in.
    isRepresentative: false,
    status: report.status as LostFoundItem['status'],
    contact: report.contact
  };
}

/** GET /api/lost-found — the shared community board. */
export async function fetchLostFoundReports(token: string): Promise<LostFoundItem[]> {
  const data = await apiRequest<Parameters<typeof mapLostFound>[0][]>('/api/lost-found', {}, token);
  return data.map(mapLostFound);
}

export async function submitLostFound(
  item: Omit<LostFoundItem, 'id' | 'status'>,
  token: string
): Promise<LostFoundItem> {
  const created = await apiRequest<Parameters<typeof mapLostFound>[0]>(
    '/api/lost-found',
    {
      method: 'POST',
      body: JSON.stringify({
        title: item.title,
        report_type: item.type,
        category: item.category,
        location: item.location,
        reported_date: item.date,
        description: item.description,
        contact: item.contact,
        // The backend writes this to disk and stores only the path, so image
        // bytes never end up in a database row.
        image_data_url: item.image || null
      })
    },
    token
  );
  return mapLostFound(created);
}
