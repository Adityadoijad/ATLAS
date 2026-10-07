export type Category =
'Mountains' |
'Beaches' |
'Cities' |
'Culture' |
'Adventure' |
'Nature' |
'Food';

export interface Destination {
  id: string;
  name: string;
  country: string;
  image: string;
  rating: number;
  reviews: number;
  budgetFrom: number;
  bestSeason: string;
  durationDays: number;
  description: string;
  categories: Category[];
  insight: string;
  highlights: string[];
  concerns: string[];
}

export interface RecommendedDestination extends Destination {
  reason: string;
}

export interface DiscoveredDestination {
  name: string;
  country: string;
  description: string;
  categories: string[];
  budgetFrom: number;
  bestSeason: string;
  durationDays: number;
  /** Real photo of the place from Wikimedia; undefined when none was found. */
  imageUrl?: string;
}

/** Attribution metadata for a Wikimedia-sourced image. All fields nullable. */
export interface ImageAttribution {
  url: string | null;
  source: string | null;
  source_url: string | null;
  author: string | null;
  license: string | null;
}

/**
 * A fully-enriched India recommendation from the backend.
 * - Groq provides: name, state, description, reason, tags
 * - Nominatim provides: latitude, longitude (coordinates are NEVER from Groq)
 * - Wikimedia provides: image (URL is NEVER from Groq)
 */
export interface DiscoverIndiaRecommendation {
  name: string;
  state: string;
  country: string;
  full_name: string;        // e.g. "Majuli, Assam, India"
  description: string;
  reason: string;
  tags: string[];
  latitude: number;
  longitude: number;
  image: ImageAttribution;
  is_fallback?: boolean;
}


export interface WeatherForecastEntry {
  timestamp: string;
  /**
   * Computed by the backend on the destination's local calendar. Deriving it
   * from `timestamp` in the browser would shift the label a day for any viewer
   * west of UTC, since a date-only string parses as UTC midnight.
   */
  weekday: string | null;
  temperatureC: number;
  condition: string;
  icon: string | null;
}

/** One day of forecast, on the destination's own local calendar. */
export interface ForecastDay {
  date: string;
  weekday: string;
  temperatureC: number;
  temperatureMinC: number;
  temperatureMaxC: number;
  condition: string | null;
  icon: string | null;
  /** 3-hourly provider steps behind this day; fewer means partial coverage. */
  stepCount: number;
  localTimeOfSummary: string;
}

/**
 * GET /api/weather/forecast.
 *
 * `isRealtimeData: false` means there is no weather to show and `days` is
 * empty — there is deliberately no estimated alternative in this shape,
 * because inventing one is the thing the whole pipeline is built to avoid.
 */
export interface DestinationForecast {
  destination: string;
  isRealtimeData: boolean;
  resolvedDestination: string | null;
  latitude: number | null;
  longitude: number | null;
  localDate: string | null;
  forecastThrough: string | null;
  days: ForecastDay[];
  unavailableReason: string | null;
}

export interface DestinationWeather {
  isRealtimeData: boolean;
  temperatureC: number | null;
  feelsLikeC: number | null;
  humidityPercent: number | null;
  windSpeedMs: number | null;
  condition: string | null;
  icon: string | null;
  forecast: WeatherForecastEntry[];
  unavailableReason: string | null;
}

export interface RealPlace {
  name: string;
  category: string | null;
  /**
   * OpenStreetMap food places carry these; OpenTripMap attractions do not.
   * Null means OSM has no such tag — render nothing rather than a placeholder.
   */
  cuisine: string | null;
  rating: number | null;
  address: string | null;
  phone: string | null;
  website: string | null;
  openingHours: string | null;
  latitude: number | null;
  longitude: number | null;
  source: string;
}

export interface DestinationDetails {
  destination: string;
  isRealtimeLocation: boolean;
  latitude: number | null;
  longitude: number | null;
  weather: DestinationWeather;
  activities: RealPlace[];
  activitiesUnavailableReason: string | null;
  restaurants: RealPlace[];
  restaurantsUnavailableReason: string | null;
}

export interface Restaurant {
  id: string;
  name: string;
  image: string;
  cuisine: string;
  city: string;
  rating: number;
  reviews: number;
  pricePerPerson: number;
  distanceKm: number;
  tags: string[];
  aiReason: string;
  insight: string;
}

export interface Activity {
  id: string;
  name: string;
  image: string;
  location: string;
  category: 'Attractions' | 'Experiences' | 'Adventure' | 'Culture' | 'Nature' | 'Hidden Gems';
  rating: number;
  reviews: number;
  price: number;
  duration: string;
  hours: string;
  aiReason: string;
}

export type TripStatus = 'upcoming' | 'past' | 'saved';

export interface Trip {
  id: string;
  destination: string;
  country: string;
  image: string;
  startDate: string;
  endDate: string;
  travelers: number;
  budget: number;
  status: TripStatus;
  /** When the trip was saved. Drives the dashboard's real activity feed. */
  createdAt?: string;
}

export type BookingStatus = 'upcoming' | 'completed' | 'cancelled';

export interface Booking {
  id: string;
  reference: string;
  title: string;
  type: 'Flight' | 'Hotel' | 'Activity' | 'Package';
  image: string;
  date: string;
  price: number;
  status: BookingStatus;
  travelers: number;
  /** When the booking was made. Drives the dashboard's real activity feed. */
  createdAt?: string;
  /**
   * True when the booking exists server-side and can therefore issue an
   * e-ticket. Seeded demo bookings and signed-out bookings have no server
   * record, so no ticket is offered for them.
   */
  persisted?: boolean;
}

/** Credit for a photo ATLAS did not take. Required by the CC licences the
 *  seeded item photos are published under. */
export interface ImageCredit {
  author?: string;
  license?: string;
  sourceUrl?: string;
}

export interface LostFoundItem {
  id: string;
  title: string;
  type: 'lost' | 'found';
  category: string;
  location: string;
  date: string;
  description: string;
  /** Empty when nobody attached a photo — the card shows a category placeholder. */
  image: string;
  imageCredit?: ImageCredit;
  /**
   * True when the photo shows this *kind* of item rather than the actual one.
   * Labelled in the UI, because on a lost-and-found board someone could
   * otherwise recognise a stock photo as their own property.
   */
  isRepresentative?: boolean;
  status: 'Open' | 'Matched' | 'Resolved';
  contact: string;
}

export interface SavedPlace {
  id: string;
  name: string;
  subtitle: string;
  image: string;
  kind: 'Destinations' | 'Hotels' | 'Restaurants' | 'Activities';
  rating: number;
}

export interface ItineraryItem {
  time: string;
  title: string;
  location: string;
  duration: string;
  cost: number;
  kind: 'travel' | 'stay' | 'food' | 'activity';
}

/** Where the traveller's journey begins. Null on trips planned before this existed. */
export interface BoardingLocation {
  name: string;
  displayName: string | null;
  latitude: number | null;
  longitude: number | null;
}

/** One stop on the trip's canonical route, in visiting order. */
export interface RouteStop {
  index: number;
  label: string;
  query: string;
  latitude: number | null;
  longitude: number | null;
  isBoarding: boolean;
  resolved: boolean;
}

/**
 * Travel between two consecutive stops.
 *
 * `distanceKm` and `durationMinutes` are null together when routing could not
 * answer. They are never 0 as a stand-in — 0 means the two stops are the same
 * place, and using it for "unknown" would claim a journey takes no time.
 */
export interface RouteLeg {
  fromIndex: number;
  toIndex: number;
  distanceKm: number | null;
  durationMinutes: number | null;
  routingAvailable: boolean;
}

/** The one ordered sequence the itinerary timeline and the map both render. */
export interface TripRoute {
  tripId: string;
  stops: RouteStop[];
  legs: RouteLeg[];
  unavailableReason: string | null;
}

export interface LocationSuggestion {
  name: string;
  displayName: string;
  latitude: number;
  longitude: number;
}

export interface ItineraryDay {
  day_number: number;
  activities: Array<{
    time: string;
    description: string;
    location?: string;
    is_realtime_data?: boolean;
    fallback?: boolean;
    is_fallback?: boolean;
  }>;
  day: number;
  title: string;
  date: string;
  items: ItineraryItem[];
}

export interface TripPlan {
  id: string;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  country: string;
  image: string;
  startDate: string;
  endDate: string;
  travelers: number;
  budget: number;
  estimatedCost: number;
  breakdown: {label: string;value: number;}[];
  days: ItineraryDay[];
  reasoning: {title: string;detail: string;}[];
  is_realtime_data?: boolean;
  data_context?: Record<string, unknown>;
  boardingLocation: BoardingLocation | null;
}

export interface PlannerPreferences {
  destination: string;
  /** Required for new trips; the itinerary's first leg originates here. */
  boardingLocation: LocationSuggestion | null;
  startDate: string;
  endDate: string;
  adults: number;
  children: number;
  interests: string[];
  transport: string[];
  accommodation: string[];
  food: string[];
  accessibility: string[];
  budget: number;
  currency: string;
  flexibleBudget: boolean;
  notes: string;
}

export interface AgentDefinition {
  id: string;
  name: string;
  task: string;
}

export type AgentPhase = 'queued' | 'running' | 'done';

export interface ChatCard {
  kind: 'destination' | 'restaurant' | 'activity' | 'hotel' | 'weather' | 'budget';
  title: string;
  subtitle: string;
  meta: string;
  image?: string;
  rating?: number;
  price?: number;
}

/**
 * Structured summary the backend attaches when the assistant has produced a
 * complete itinerary. Its presence is what gates the "Proceed to Booking"
 * CTA — the frontend never infers a finished plan from the reply's wording.
 */
export interface AssistantPlan {
  title: string;
  destination: string;
  startDate: string;
  endDate: string;
  travelers: number;
  estimatedCost: number;
  currency: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  time: string;
  cards?: ChatCard[];
  /** Set only on a reply that completed a full trip plan. */
  plan?: AssistantPlan;
}

export interface Conversation {
  id: string;
  title: string;
  updated: string;
  messages: ChatMessage[];
}
