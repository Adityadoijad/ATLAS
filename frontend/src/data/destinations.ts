import { Destination } from '../types';

export const IMAGES = {
  heroLake: "/998ad918-016b-47fa-b81f-c4b22e00d24a.jpg",
  goa: "/goa.png",
  kerala: "/kerala.png",
  kolkata: "/kolkata.png",
  mussoorie: "/mussoorie.png",
  mumbai: "/mumbai.png",
  foodLocal: "/4850d186-be61-4188-be46-379c78aced34.jpg",
  foodStreet: "/120bcd39-8958-4b38-9556-43e1c3314097.jpg",
  foodFine: "/3c80af2d-99f5-4a04-ac8f-a5530426226d.jpg",
  trek: "/e365dde7-9421-491f-8a47-2dd786585015.jpg",
  culture: "/95534c07-263b-4244-9d9b-ff0e594d8322.jpg",
  kyoto: "/64884a2b-e055-4153-9bdb-2ac3542f3ae6.jpg",
  santorini: "/abb44cca-7476-456b-987c-0e76a111e3ff.jpg",
  bali: "/ac2e119f-65ca-4e4f-997a-ec102d01a2ae.jpg",
  manali: "/7081e96c-9d41-4635-ba0d-9316c4886606.jpg",
  jaipur: "/f58d8a15-524b-44fd-8c02-18e4f4f3db05.jpg",
  dubai: "/7c8cc87c-7d11-4e98-aa4b-266f7ff43db2.jpg",
  swissAlps: "/b6de9981-f5f1-41f6-bde5-3be277e6375e.jpg"
};

export const destinations: Destination[] = [
{
  id: 'kerala',
  name: 'Kerala',
  country: 'India',
  image: IMAGES.kerala,
  rating: 4.8,
  reviews: 22400,
  budgetFrom: 21000,
  bestSeason: 'Sep – Mar',
  durationDays: 6,
  description: 'Backwater cruises, tea hills and ayurveda retreats along the Malabar coast.',
  categories: ['Nature', 'Beaches', 'Food'],
  insight: 'Travellers rate overnight houseboats in Alleppey as the single best experience.',
  highlights: ['Calm pace', 'Great vegetarian food', 'Elder friendly'],
  concerns: ['Humidity', 'Long transfer times']
},
{
  id: 'kolkata',
  name: 'Kolkata',
  country: 'India',
  image: IMAGES.kolkata,
  rating: 4.7,
  reviews: 19800,
  budgetFrom: 12000,
  bestSeason: 'Oct – Mar',
  durationDays: 3,
  description: 'Historical architecture, vibrant culture, and the famous street food of the City of Joy.',
  categories: ['Culture', 'Cities', 'Food'],
  insight: 'Community reports suggest visiting during Durga Puja for an unparalleled cultural experience.',
  highlights: ['Victoria Memorial', 'Rich heritage', 'Incredible food'],
  concerns: ['High humidity in summer', 'Heavy traffic']
},
{
  id: 'mussoorie',
  name: 'Mussoorie',
  country: 'India',
  image: IMAGES.mussoorie,
  rating: 4.6,
  reviews: 15300,
  budgetFrom: 14000,
  bestSeason: 'Mar – Jun',
  durationDays: 4,
  description: 'The Queen of Hills, offering majestic views of the Shivalik range and Doon Valley.',
  categories: ['Mountains', 'Nature', 'Cities'],
  insight: 'Take a walk on the Camel Back Road for beautiful and peaceful sunset views.',
  highlights: ['Mall Road strolls', 'Scenic waterfalls', 'Pleasant climate'],
  concerns: ['Crowded in peak summer', 'Cold in winter']
},
{
  id: 'goa',
  name: 'Goa',
  country: 'India',
  image: IMAGES.goa,
  rating: 4.6,
  reviews: 42130,
  budgetFrom: 18500,
  bestSeason: 'Nov – Feb',
  durationDays: 4,
  description: 'Beach shacks, Portuguese heritage lanes and India’s most relaxed coastline.',
  categories: ['Beaches', 'Food', 'Culture'],
  insight: 'Travellers frequently mention South Goa for quiet beaches and authentic local seafood.',
  highlights: ['Budget friendly', 'Great nightlife', 'Easy scooter travel'],
  concerns: ['Monsoon closures', 'Crowded North Goa in December']
},
{
  id: 'mumbai',
  name: 'Mumbai',
  country: 'India',
  image: IMAGES.mumbai,
  rating: 4.9,
  reviews: 45200,
  budgetFrom: 25000,
  bestSeason: 'Nov – Feb',
  durationDays: 3,
  description: 'The city of dreams, home to historic monuments, a fast-paced lifestyle, and coastal views.',
  categories: ['Cities', 'Culture', 'Food'],
  insight: 'Marine Drive at night is highly recommended for a relaxing evening by the sea.',
  highlights: ['Gateway of India', 'Vibrant nightlife', 'Iconic street food'],
  concerns: ['Heavy traffic', 'Expensive accommodation']
},
{
  id: 'manali',
  name: 'Manali',
  country: 'India',
  image: IMAGES.manali,
  rating: 4.7,
  reviews: 28900,
  budgetFrom: 16000,
  bestSeason: 'Mar – Jun',
  durationDays: 5,
  description: 'Snow-capped Himalayan peaks, pine forests and adventure sports in the Kullu valley.',
  categories: ['Mountains', 'Adventure', 'Nature'],
  insight: 'Solang Valley is best visited early morning before tour buses arrive.',
  highlights: ['Paragliding', 'River rafting', 'Snow trekking'],
  concerns: ['Roads close in heavy snow', 'Crowded during holidays']
},
{
  id: 'jaipur',
  name: 'Jaipur',
  country: 'India',
  image: IMAGES.jaipur,
  rating: 4.7,
  reviews: 31500,
  budgetFrom: 15000,
  bestSeason: 'Oct – Mar',
  durationDays: 4,
  description: 'The Pink City — grand forts, royal palaces and vibrant bazaars of Rajasthan.',
  categories: ['Culture', 'Cities', 'Adventure'],
  insight: 'Amber Fort at sunrise avoids both the heat and the crowds.',
  highlights: ['Hawa Mahal', 'Amber Fort', 'Rajasthani cuisine'],
  concerns: ['Very hot summers', 'Persistent souvenir sellers']
},
{
  id: 'kyoto',
  name: 'Kyoto',
  country: 'Japan',
  image: IMAGES.kyoto,
  rating: 4.9,
  reviews: 26700,
  budgetFrom: 110000,
  bestSeason: 'Mar – May',
  durationDays: 6,
  description: 'Thousands of temples, geisha districts and bamboo groves in Japan’s cultural heart.',
  categories: ['Culture', 'Nature', 'Food'],
  insight: 'Arashiyama Bamboo Grove is calmest right after sunrise.',
  highlights: ['Fushimi Inari Shrine', 'Kaiseki dining', 'Cherry blossoms'],
  concerns: ['Peak season pricing', 'Limited English signage']
},
{
  id: 'bali',
  name: 'Bali',
  country: 'Indonesia',
  image: IMAGES.bali,
  rating: 4.7,
  reviews: 38200,
  budgetFrom: 65000,
  bestSeason: 'Apr – Oct',
  durationDays: 6,
  description: 'Rice terraces, surf breaks and temple ceremonies across the Island of the Gods.',
  categories: ['Beaches', 'Nature', 'Adventure'],
  insight: 'Ubud’s rice terraces are least crowded on weekday mornings.',
  highlights: ['Uluwatu surf', 'Rice terrace treks', 'Temple ceremonies'],
  concerns: ['Traffic in Canggu/Seminyak', 'Monsoon season flooding']
},
{
  id: 'santorini',
  name: 'Santorini',
  country: 'Greece',
  image: IMAGES.santorini,
  rating: 4.8,
  reviews: 24100,
  budgetFrom: 145000,
  bestSeason: 'Jun – Sep',
  durationDays: 5,
  description: 'Whitewashed cliffside villages overlooking the Aegean’s most famous caldera sunsets.',
  categories: ['Beaches', 'Culture', 'Nature'],
  insight: 'Oia’s sunset viewpoint fills up an hour early — arrive by 6pm in summer.',
  highlights: ['Caldera sunsets', 'Volcanic beaches', 'Cliffside dining'],
  concerns: ['Expensive in peak season', 'Very touristy in July–Aug']
},
{
  id: 'dubai',
  name: 'Dubai',
  country: 'UAE',
  image: IMAGES.dubai,
  rating: 4.6,
  reviews: 33400,
  budgetFrom: 85000,
  bestSeason: 'Nov – Mar',
  durationDays: 4,
  description: 'Futuristic skylines, desert safaris and luxury shopping in the heart of the Gulf.',
  categories: ['Cities', 'Adventure', 'Culture'],
  insight: 'Desert safaris are noticeably cooler and less crowded at sunset.',
  highlights: ['Burj Khalifa', 'Desert safari', 'Gold Souk'],
  concerns: ['Extreme summer heat', 'Higher daily costs']
},
{
  id: 'swiss-alps',
  name: 'Swiss Alps',
  country: 'Switzerland',
  image: IMAGES.swissAlps,
  rating: 4.9,
  reviews: 19800,
  budgetFrom: 175000,
  bestSeason: 'Jun – Sep',
  durationDays: 6,
  description: 'Alpine lakes, cable-car summits and postcard villages across the Swiss highlands.',
  categories: ['Mountains', 'Nature', 'Adventure'],
  insight: 'Early morning trains to Jungfraujoch avoid both crowds and cloud cover.',
  highlights: ['Cable car summits', 'Alpine lakes', 'Scenic rail routes'],
  concerns: ['High cost of travel', 'Weather-dependent visibility']
}
];


export const popularSearches = ['Kerala', 'Goa', 'Mumbai', 'Kolkata', 'Mussoorie'];

export const categoryPills: string[] = [
'All',
'Mountains',
'Beaches',
'Cities',
'Culture',
'Adventure',
'Nature',
'Food'];


export function findDestination(id: string) {
  return destinations.find((d) => d.id === id);
}

export function findDestinationByName(name: string) {
  const normalized = name.trim().toLowerCase();
  return destinations.find((d) => d.name.toLowerCase() === normalized);
}