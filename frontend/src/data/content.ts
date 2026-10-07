import { AgentDefinition } from '../types';

export const features = [
{
  icon: 'Sparkles',
  title: 'Intelligent Travel Planning',
  description: 'Describe the trip you want in plain language and get a structured, day-by-day plan.'
},
{
  icon: 'Network',
  title: 'Multi-Agent Intelligence',
  description: 'Specialised agents research routes, stays, food and weather in parallel.'
},
{
  icon: 'UserRoundCheck',
  title: 'Personalized Recommendations',
  description: 'Every suggestion is scored against your interests, pace and accessibility needs.'
},
{
  icon: 'Wallet',
  title: 'Budget Optimization',
  description: 'A dedicated optimizer keeps the itinerary inside your budget and shows the trade-offs.'
},
{
  icon: 'MessageSquareQuote',
  title: 'Review Intelligence',
  description: 'Thousands of traveller reviews summarised into positives, concerns and crowd levels.'
},
{
  icon: 'Users',
  title: 'Community Travel Insights',
  description: 'Real reports from recent travellers on timing, safety and hidden alternatives.'
},
{
  icon: 'Languages',
  title: 'Multilingual Access',
  description: 'Plan in English, Hindi, Marathi, Tamil and six more Indian languages.'
},
{
  icon: 'Mic',
  title: 'Voice Assistance',
  description: 'Speak to ATLAS while travelling and get hands-free answers and updates.'
},
{
  icon: 'CalendarSync',
  title: 'Dynamic Itinerary Planning',
  description: 'Change a day, a budget or the weather and the plan re-solves around it.'
}];


export const agents: AgentDefinition[] = [
{ id: 'planner', name: 'Planner Agent', task: 'Understanding your preferences' },
{ id: 'travel', name: 'Travel Agent', task: 'Analyzing transportation' },
{ id: 'hotel', name: 'Hotel Agent', task: 'Finding suitable stays' },
{ id: 'food', name: 'Food Agent', task: 'Finding local food' },
{ id: 'activity', name: 'Activity Agent', task: 'Finding experiences' },
{ id: 'weather', name: 'Weather Agent', task: 'Checking conditions' },
{ id: 'maps', name: 'Maps Agent', task: 'Optimizing routes' },
{ id: 'review', name: 'Review Intelligence', task: 'Analyzing traveller experiences' },
{ id: 'budget', name: 'Budget Optimizer', task: 'Checking your budget' }];


export const pipeline = [
{ label: 'User', detail: 'You describe the trip you want' },
{ label: 'Travel Requirements', detail: 'Dates, travellers, budget, interests' },
{ label: 'Planner Agent', detail: 'Breaks the request into tasks' },
{ label: 'Specialised Agents', detail: 'Travel · Hotel · Food · Activity · Weather · Maps · Reviews' },
{ label: 'Budget Optimizer', detail: 'Balances cost against experience' },
{ label: 'Constraint Solver', detail: 'Fits everything into real hours and distances' },
{ label: 'Itinerary Generator', detail: 'Builds the day-by-day plan' },
{ label: 'Personalized Travel Plan', detail: 'Reviewed and edited by you' },
{ label: 'Mock Booking', detail: 'Demonstration booking with confirmation' }];


export const interests = [
'Adventure',
'Nature',
'Beaches',
'History',
'Culture',
'Shopping',
'Nightlife',
'Photography',
'Food',
'Relaxation',
'Spiritual',
'Wildlife'];


export const transportOptions = ['Flight', 'Train', 'Bus', 'Car', 'Local Transport'];
export const accommodationOptions = ['Hotel', 'Hostel', 'Resort', 'Homestay'];
export const foodOptions = [
'Vegetarian',
'Vegan',
'Non-vegetarian',
'Local cuisine',
'Street food',
'Fine dining',
'Budget-friendly'];

export const accessibilityOptions = [
'Wheelchair accessible',
'Elder-friendly',
'Child-friendly',
'Medical accessibility'];


export const languages = [
{ code: 'en', label: 'English', native: 'English' },
{ code: 'hi', label: 'Hindi', native: 'हिन्दी' },
{ code: 'mr', label: 'Marathi', native: 'मराठी' },
{ code: 'bn', label: 'Bengali', native: 'বাংলা' },
{ code: 'ta', label: 'Tamil', native: 'தமிழ்' },
{ code: 'te', label: 'Telugu', native: 'తెలుగు' },
{ code: 'gu', label: 'Gujarati', native: 'ગુજરાતી' },
{ code: 'kn', label: 'Kannada', native: 'ಕನ್ನಡ' },
{ code: 'ml', label: 'Malayalam', native: 'മലയാളം' }];


export const suggestedPrompts = [
'Plan a 5-day trip under ₹30,000',
'Find hidden gems',
'Suggest local restaurants',
'Optimize my itinerary',
'What should I pack?',
"Check tomorrow's weather"];