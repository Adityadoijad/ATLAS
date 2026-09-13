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
}

export interface WeatherForecastEntry {
  timestamp: string;
  temperatureC: number;
  condition: string;
  icon: string | null;
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
  rating: number | null;
  address: string | null;
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
  progress: number;
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
}

export interface LostFoundItem {
  id: string;
  title: string;
  type: 'lost' | 'found';
  category: string;
  location: string;
  date: string;
  description: string;
  image: string;
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
  rating: number;
  distanceKm: number;
  kind: 'travel' | 'stay' | 'food' | 'activity';
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
  weather: {day: string;temp: number;condition: string;}[];
  days: ItineraryDay[];
  reasoning: {title: string;detail: string;}[];
  is_realtime_data?: boolean;
  data_context?: Record<string, unknown>;
}

export interface PlannerPreferences {
  destination: string;
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

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  time: string;
  cards?: ChatCard[];
}

export interface Conversation {
  id: string;
  title: string;
  updated: string;
  messages: ChatMessage[];
}
