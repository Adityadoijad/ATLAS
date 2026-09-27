import { Activity, Booking, LostFoundItem, Restaurant, SavedPlace, Trip } from '../types';
import { IMAGES } from './destinations';

export const restaurants: Restaurant[] = [
{
  id: 'r1',
  name: 'Gunpowder',
  image: IMAGES.foodLocal,
  cuisine: 'South Indian',
  city: 'Assagao, Goa',
  rating: 4.8,
  reviews: 2140,
  pricePerPerson: 900,
  distanceKm: 2.4,
  tags: ['Local food', 'Vegetarian', 'Fine dining'],
  aiReason: 'Matches your interest in local cuisine and sits 8 minutes from your stay.',
  insight: 'Travellers frequently mention this place for authentic coastal thalis and calm seating.'
},
{
  id: 'r2',
  name: 'Vinayak Family Restaurant',
  image: IMAGES.foodStreet,
  cuisine: 'Goan Seafood',
  city: 'Assagao, Goa',
  rating: 4.6,
  reviews: 5610,
  pricePerPerson: 650,
  distanceKm: 3.9,
  tags: ['Non-vegetarian', 'Budget-friendly', 'Local food'],
  aiReason: 'Best value seafood within your food budget for day two.',
  insight: 'Reviewers say to arrive before 8pm — waiting times climb sharply after that.'
},
{
  id: 'r3',
  name: 'Bomras',
  image: IMAGES.foodFine,
  cuisine: 'Burmese',
  city: 'Candolim, Goa',
  rating: 4.7,
  reviews: 1890,
  pricePerPerson: 1800,
  distanceKm: 6.1,
  tags: ['Fine dining', 'Non-vegetarian'],
  aiReason: 'A higher-spend evening that still fits your flexible budget.',
  insight: 'Consistently rated for service quality; reservations strongly recommended.'
},
{
  id: 'r4',
  name: 'Baba Au Rhum',
  image: IMAGES.foodFine,
  cuisine: 'European Bakery',
  city: 'Anjuna, Goa',
  rating: 4.5,
  reviews: 3320,
  pricePerPerson: 750,
  distanceKm: 4.7,
  tags: ['Vegetarian', 'Budget-friendly'],
  aiReason: 'Quiet morning spot that matches your preference for less crowded places.',
  insight: 'Community reports call the garden seating the calmest breakfast option in North Goa.'
},
{
  id: 'r5',
  name: 'Anandashram',
  image: IMAGES.foodLocal,
  cuisine: 'Malvani',
  city: 'Panjim, Goa',
  rating: 4.4,
  reviews: 2760,
  pricePerPerson: 450,
  distanceKm: 11.2,
  tags: ['Local food', 'Street food', 'Budget-friendly'],
  aiReason: 'Highest rated budget option near your Panjim heritage walk.',
  insight: 'Travellers describe it as a genuine local canteen rather than a tourist restaurant.'
},
{
  id: 'r6',
  name: 'Bombay Canteen',
  image: IMAGES.foodFine,
  cuisine: 'Modern Indian',
  city: 'Lower Parel, Mumbai',
  rating: 4.9,
  reviews: 980,
  pricePerPerson: 2600,
  distanceKm: 1.1,
  tags: ['Fine dining', 'Local food'],
  aiReason: 'Top-rated near your Mumbai stay with great ambience.',
  insight: 'Highly recommended to book ahead for weekend dinners.'
}];


export const activities: Activity[] = [
{
  id: 'a1',
  name: 'Sunrise Ridge Trek',
  image: IMAGES.trek,
  location: 'Sethan, Manali',
  category: 'Adventure',
  rating: 4.8,
  reviews: 1420,
  price: 1800,
  duration: '4 hrs',
  hours: '05:00 – 11:00',
  aiReason: 'Matches your adventure interest and avoids the crowded Solang route.'
},
{
  id: 'a2',
  name: 'Old City Heritage Walk',
  image: IMAGES.culture,
  location: 'Panjim, Goa',
  category: 'Culture',
  rating: 4.6,
  reviews: 890,
  price: 700,
  duration: '2.5 hrs',
  hours: '08:00 – 18:00',
  aiReason: 'Low crowd levels in the morning and close to your hotel.'
},
{
  id: 'a3',
  name: 'Backwater Houseboat Cruise',
  image: IMAGES.kerala,
  location: 'Alleppey, Kerala',
  category: 'Experiences',
  rating: 4.9,
  reviews: 3210,
  price: 6500,
  duration: 'Overnight',
  hours: 'Check-in 12:00',
  aiReason: 'Rated the single best experience in Kerala by our community data.'
},
{
  id: 'a4',
  name: 'Gateway of India Early Access',
  image: IMAGES.mumbai,
  location: 'Mumbai, India',
  category: 'Attractions',
  rating: 4.9,
  reviews: 8740,
  price: 0,
  duration: '2 hrs',
  hours: 'Open 24 hrs',
  aiReason: 'Visit before 07:00 to avoid the crowd levels reported by most travellers.'
},
{
  id: 'a5',
  name: 'Hidden Waterfall Trail',
  image: IMAGES.manali,
  location: 'Jibhi, Himachal',
  category: 'Hidden Gems',
  rating: 4.7,
  reviews: 410,
  price: 500,
  duration: '3 hrs',
  hours: '07:00 – 17:00',
  aiReason: 'Low footfall alternative you asked for — quiet, and under budget.'
},
{
  id: 'a6',
  name: 'Sundown Cruise',
  image: IMAGES.kolkata,
  location: 'Hooghly River, Kolkata',
  category: 'Adventure',
  rating: 4.5,
  reviews: 6120,
  price: 2200,
  duration: '3 hrs',
  hours: '16:00 – 19:00',
  aiReason: 'Family-friendly operator with seating, matching your accessibility needs.'
},
{
  id: 'a7',
  name: 'Tea Garden Walk',
  image: IMAGES.mussoorie,
  location: 'Mussoorie, India',
  category: 'Nature',
  rating: 4.7,
  reviews: 2280,
  price: 600,
  duration: '2 hrs',
  hours: '06:30 – 12:00',
  aiReason: 'Fits your nature interest and the cooler part of the day.'
},
{
  id: 'a8',
  name: 'Amber Fort Guided Tour',
  image: IMAGES.jaipur,
  location: 'Jaipur, Rajasthan',
  category: 'Attractions',
  rating: 4.6,
  reviews: 9450,
  price: 1200,
  duration: '3 hrs',
  hours: '08:00 – 17:30',
  aiReason: 'Elder-friendly route with vehicle access to the upper courtyard.'
}];


export const trips: Trip[] = [
{
  id: 't1',
  destination: 'Goa',
  country: 'India',
  image: IMAGES.goa,
  startDate: '2026-09-12',
  endDate: '2026-09-16',
  travelers: 2,
  budget: 48000,
  status: 'upcoming',
  progress: 80
},
{
  id: 't2',
  destination: 'Mumbai',
  country: 'India',
  image: IMAGES.mumbai,
  startDate: '2026-11-04',
  endDate: '2026-11-10',
  travelers: 2,
  budget: 45000,
  status: 'upcoming',
  progress: 35
},
{
  id: 't3',
  destination: 'Manali',
  country: 'India',
  image: IMAGES.manali,
  startDate: '2026-03-08',
  endDate: '2026-03-13',
  travelers: 4,
  budget: 62000,
  status: 'past',
  progress: 100
},
{
  id: 't4',
  destination: 'Kerala',
  country: 'India',
  image: IMAGES.kerala,
  startDate: '2025-12-20',
  endDate: '2025-12-26',
  travelers: 3,
  budget: 88000,
  status: 'past',
  progress: 100
},
{
  id: 't5',
  destination: 'Ladakh',
  country: 'India',
  image: IMAGES.swissAlps,
  startDate: '2027-06-14',
  endDate: '2027-06-21',
  travelers: 2,
  budget: 96000,
  status: 'saved',
  progress: 15
}];


export const bookings: Booking[] = [
{
  id: 'b1',
  reference: 'ATL-9F2K41',
  title: 'Goa · Beach Escape Package',
  type: 'Package',
  image: IMAGES.goa,
  date: '2026-09-12',
  price: 42800,
  status: 'upcoming',
  travelers: 2
},
{
  id: 'b2',
  reference: 'ATL-3D8P77',
  title: 'Mumbai · Marine Drive Stay',
  type: 'Hotel',
  image: IMAGES.mumbai,
  date: '2026-11-04',
  price: 45000,
  status: 'upcoming',
  travelers: 2
},
{
  id: 'b3',
  reference: 'ATL-1A5Q02',
  title: 'Manali · Sunrise Ridge Trek',
  type: 'Activity',
  image: IMAGES.trek,
  date: '2026-03-10',
  price: 7200,
  status: 'completed',
  travelers: 4
},
{
  id: 'b4',
  reference: 'ATL-7C4M18',
  title: 'Kerala · Alleppey Houseboat',
  type: 'Activity',
  image: IMAGES.kerala,
  date: '2025-12-22',
  price: 19500,
  status: 'completed',
  travelers: 3
},
{
  id: 'b5',
  reference: 'ATL-6B9X30',
  title: 'Kolkata · Return Flight',
  type: 'Flight',
  image: IMAGES.kolkata,
  date: '2026-01-18',
  price: 8400,
  status: 'cancelled',
  travelers: 1
}];


export const lostFoundItems: LostFoundItem[] = [
{
  id: 'lf1',
  title: 'Black DSLR camera bag',
  type: 'lost',
  category: 'Electronics',
  location: 'Baga Beach, Goa',
  date: '2026-08-02',
  description: 'Left near the shack seating around sunset. Contains a lens cap and a blue strap.',
  image: '/lost-found/camera-bag.jpg',
  imageCredit: { author: 'FASTILY', license: 'CC BY-SA 4.0', sourceUrl: 'https://commons.wikimedia.org/wiki/File:Nikon_Camera_Bag_1_2019-03-07.jpg' },
  isRepresentative: true,
  status: 'Open',
  contact: 'In-app message'
},
{
  id: 'lf2',
  title: 'Passport wallet (navy)',
  type: 'found',
  category: 'Documents',
  location: 'Leh Airport, Ladakh',
  date: '2026-07-28',
  description: 'Found at the domestic arrivals bench. Handed to the airport help desk.',
  image: '/lost-found/passport-wallet.jpg',
  imageCredit: { author: 'Rojasoscar1', license: 'CC BY-SA 4.0', sourceUrl: 'https://commons.wikimedia.org/wiki/File:Current_cover_Costa_Rican_passport.jpg' },
  isRepresentative: true,
  status: 'Matched',
  contact: 'Email'
},
{
  id: 'lf3',
  title: 'Trekking pole pair',
  type: 'found',
  category: 'Gear',
  location: 'Sethan Trail, Manali',
  date: '2026-07-19',
  description: 'Left at the second viewpoint. Currently with the Sethan homestay owner.',
  image: '/lost-found/trekking-poles.jpg',
  imageCredit: { author: 'Daniel Case', license: 'CC BY-SA 3.0', sourceUrl: 'https://commons.wikimedia.org/wiki/File:Trekking_poles.jpg' },
  isRepresentative: true,
  status: 'Open',
  contact: 'Phone'
},
{
  id: 'lf4',
  title: 'Silver bracelet with charm',
  type: 'lost',
  category: 'Jewellery',
  location: 'Fort Kochi, Kerala',
  date: '2026-06-30',
  description: 'Lost during the evening heritage walk near the Chinese fishing nets.',
  image: '/lost-found/silver-bangle.jpg',
  imageCredit: { author: 'SpeakingArch', license: 'CC BY-SA 4.0', sourceUrl: 'https://commons.wikimedia.org/wiki/File:Thela,_Silver_Bangle,_Jharkhand,_India.jpg' },
  isRepresentative: true,
  status: 'Resolved',
  contact: 'In-app message'
}];


export const savedPlaces: SavedPlace[] = [
{ id: 's1', name: 'Mumbai, India', subtitle: 'India · Culture', image: IMAGES.mumbai, kind: 'Destinations', rating: 4.9 },
{ id: 's2', name: 'Kolkata, India', subtitle: 'India · Cities', image: IMAGES.kolkata, kind: 'Destinations', rating: 4.8 },
{ id: 's3', name: 'Marine Drive Boutique Stay', subtitle: 'Mumbai · ₹8,400/night', image: IMAGES.culture, kind: 'Hotels', rating: 4.7 },
{ id: 's4', name: 'Backwater Villa', subtitle: 'Alleppey, Kerala · ₹6,800/night', image: IMAGES.kerala, kind: 'Hotels', rating: 4.6 },
{ id: 's5', name: 'Gunpowder', subtitle: 'South Indian · ₹900 per person', image: IMAGES.foodLocal, kind: 'Restaurants', rating: 4.8 },
{ id: 's6', name: 'Bombay Canteen', subtitle: 'Modern Indian · ₹2,600 per person', image: IMAGES.foodFine, kind: 'Restaurants', rating: 4.9 },
{ id: 's7', name: 'Sunrise Ridge Trek', subtitle: 'Manali · 4 hrs', image: IMAGES.trek, kind: 'Activities', rating: 4.8 },
{ id: 's8', name: 'Old City Heritage Walk', subtitle: 'Panjim · 2.5 hrs', image: IMAGES.culture, kind: 'Activities', rating: 4.6 }];