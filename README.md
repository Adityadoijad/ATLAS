# ATLAS — Where Travel Meets AI

> **AI-Powered Multi-Agent Travel Planning and Decision Support Platform**

ATLAS is an AI-powered travel platform designed to help users **discover destinations, plan trips, generate personalized itineraries, optimize travel decisions, and manage their journeys** through a coordinated multi-agent architecture.

Unlike a conventional travel recommendation system, ATLAS combines multiple specialized AI agents with user preferences, budget constraints, weather, routes, activities, food, accommodation, and traveler insights to create a personalized travel plan.

---

## 🚀 Key Features

* **AI-Powered Travel Planning** — Generate personalized travel plans based on user requirements.
* **Multi-Agent Architecture** — Specialized agents collaborate to handle different aspects of travel planning.
* **Personalized Itineraries** — Generate day-by-day travel schedules based on preferences and constraints.
* **Travel Recommendations** — Recommend destinations, activities, hotels, restaurants, and experiences.
* **Budget Optimization** — Evaluate travel options against the user's available budget.
* **Constraint-Based Planning** — Consider budget, travel time, ratings, interests, weather, opening hours, and accessibility.
* **AI Travel Assistant** — Interactive assistant for travel-related questions and trip modifications.
* **Weather Intelligence** — Incorporate weather information into travel decisions.
* **Maps & Route Intelligence** — Analyze locations and travel routes.
* **Review Intelligence** — Use traveler/community insights to improve recommendations.
* **Multilingual Access** — Designed to support multiple languages.
* **Voice Assistance** — Voice interaction capability for the AI travel assistant.
* **Lost & Found** — Community-based reporting and discovery of lost or found items in travel locations.
* **Mock Booking System** — Demonstrates the complete booking workflow without real payment processing.
* **Trip Management** — Manage upcoming, completed, and saved trips.

---

## 🧠 Multi-Agent Architecture

ATLAS uses a master **Planner Agent** to coordinate specialized agents.

```text
                         User
                           │
                           ▼
                  Travel Requirements
                           │
                           ▼
                    Planner Agent
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   Travel Agent       Hotel Agent        Activity Agent
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                    Food Agent
                           │
                           ▼
                    Weather Agent
                           │
                           ▼
                     Maps Agent
                           │
                           ▼
                Review Intelligence
                           │
                           ▼
                  Budget Optimizer
                           │
                           ▼
                  Constraint Solver
                           │
                           ▼
              Itinerary Generator
                           │
                           ▼
              Personalized Itinerary
                           │
                           ▼
                    User Review
                           │
                           ▼
                    Mock Booking
```

The architecture is designed so that each specialized agent focuses on a particular travel domain while the Planner Agent coordinates the overall planning process.

---

## 🛠️ Technology Stack

### Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS
* Component-based UI architecture

### Backend

* FastAPI
* Python

### AI

* **Groq** — LLM inference provider (OpenAI-compatible chat completions)
* **Model:** `openai/gpt-oss-120b` (open-weight), configurable via `GROQ_MODEL`
* Multi-Agent Architecture
* AI-based planning and decision making

All LLM calls are centralized in `backend/app/services/ai_service.py` — agents
never call the provider SDK directly, so swapping providers is a change to
that one module.

**Required environment variables** (`backend/.env`, copy from `.env.example`):

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b
```

Get a free key (no card required) at <https://console.groq.com/keys>. To list
the models your account can actually use:

```bash
curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
```

Never commit real API keys — `.env` is gitignored.

### Database

* PostgreSQL / Supabase

### External Services

All external calls are made server-side from FastAPI. No third-party service
URL or credential is ever exposed to the React app.

| Data | Provider | Cost | API key |
| --- | --- | --- | --- |
| Geocoding | OpenStreetMap / Nominatim | Free | Not required |
| Food places | OpenStreetMap / Overpass | Free | **Not required** |
| Weather | OpenWeatherMap | Free tier | `OPENWEATHER_API_KEY` |
| Attractions | OpenTripMap | Free tier | `OPENTRIPMAP_API_KEY` |
| Destination photos | Wikimedia | Free | Not required |

#### Food data (OpenStreetMap / Overpass)

* **Endpoint:** `https://overpass-api.de/api/interpreter` (POST, Overpass QL)
* **Cost:** free. **No API key** is required for ordinary map-data queries, so
  there is deliberately no `OVERPASS_API_KEY` setting.
* **Data returned:** restaurants, cafes, fast food, food courts, bakeries and
  ice cream shops (pubs and bars only when the traveller asks for nightlife),
  with coordinates plus whatever OSM has been tagged with — cuisine, address,
  phone, website and opening hours.

**What "live food data" means here.** It means *current OpenStreetMap-listed
place information*. It does **not** mean real-time table availability, and it
does **not** mean menu pricing:

* **Place information** (name, cuisine, contact, opening hours) — live OSM data.
* **Meal cost** — an AI estimate. OSM publishes no reliable prices, so costs are
  never presented as live, even when the place data is.

**Limitations.** OSM coverage is uneven; a venue may exist with nothing but a
name, and missing tags are returned as `null` rather than filled in. Opening
hours are as last edited by a contributor, not a live status.

**Usage policy.** The public Overpass servers are donated shared infrastructure
with usage limits. ATLAS caches results per area for 20 minutes, collapses
concurrent requests for the same area into one call, sends an identifying
User-Agent, and never retries a rate-limited (HTTP 429/504) response — it falls
back to estimates instead.

**Attribution.** OSM data is licensed under the
[ODbL](https://www.openstreetmap.org/copyright). Anywhere ATLAS shows this data
it displays "Food place data © OpenStreetMap contributors", linking to the
copyright page. Do not remove that attribution.

---

## 📁 Project Structure

```text
ATLAS/
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── services/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   ├── utils/
│   └── public/
│
├── backend/
│   ├── app/
│   ├── agents/
│   ├── api/
│   ├── models/
│   ├── services/
│   └── database/
│
├── docs/
│   ├── architecture/
│   ├── research/
│   └── project/
│
├── .gitignore
├── README.md
└── docker-compose.yml
```

The structure may evolve as development progresses.

---

## 🔄 Core Workflow

```text
User Authentication
        ↓
Enter Travel Requirements
        ↓
Planner Agent
        ↓
Specialized Travel Agents
        ↓
Data Collection & Analysis
        ↓
Budget Optimization
        ↓
Constraint Solving
        ↓
Personalized Itinerary
        ↓
User Reviews / Modifies Suggestions
        ↓
Mock Booking
        ↓
Booking Confirmation
        ↓
Trip Dashboard
```

---

## 👤 Travel Requirements

Users can provide:

* Destination
* Travel dates
* Number of travelers
* Budget
* Interests
* Transportation preference
* Accommodation preference
* Food preference
* Accessibility requirements
* Additional personal preferences

These requirements are used by the planning system to generate a personalized travel plan.

---

## 📊 Decision Factors

ATLAS can consider multiple constraints while generating recommendations:

| Factor           | Purpose                                         |
| ---------------- | ----------------------------------------------- |
| Budget           | Keep the trip within the user's financial limit |
| Travel Time      | Reduce unnecessary travel                       |
| Ratings          | Prioritize highly rated options                 |
| Interests        | Match activities with user preferences          |
| Weather          | Adapt recommendations to conditions             |
| Opening Hours    | Avoid unavailable attractions                   |
| Accessibility    | Consider accessibility requirements             |
| Location         | Optimize distances and routes                   |
| Food Preferences | Match restaurants with dietary preferences      |

---

## 💬 AI Travel Assistant

The AI Travel Assistant provides an interactive interface for users to:

* Ask travel questions
* Modify their trip
* Discover destinations
* Find activities
* Find restaurants
* Optimize an itinerary
* Request travel suggestions
* Ask for travel tips

The assistant is integrated into the broader ATLAS travel-planning workflow rather than functioning as an isolated chatbot.

---

## 🌍 Community Features

### Lost & Found

Travelers and local users can report lost or found items associated with a particular location.

Users can provide:

* Item
* Category
* Location
* Date
* Description
* Image
* Contact preference

This creates a community layer around the travel platform.

---

## 📱 User Dashboard

The dashboard provides access to:

* Upcoming trips
* Active itineraries
* Booking history
* Saved places
* AI recommendations
* Recent activity
* Travel preferences
* Lost & Found

---

## 🔐 Security

The application is designed with a separated frontend/backend architecture.

Security considerations include:

* Authentication
* Authorization
* Environment variables for secrets
* Secure API communication
* Database access controls
* Input validation
* Protection of API credentials

**API keys and credentials must never be committed to GitHub.**

---

## 🧪 Current Development Status

### Completed / In Progress

* [x] ATLAS project concept
* [x] Multi-agent architecture design
* [x] Travel planning workflow
* [x] Frontend UI development
* [x] Core travel interface
* [ ] Backend API
* [ ] Database integration
* [ ] AI agent implementation
* [ ] Weather integration
* [ ] Maps integration
* [ ] Review/community data integration
* [ ] Voice assistance
* [ ] Multilingual support
* [ ] Mock booking integration
* [ ] End-to-end testing
* [ ] Cloud deployment

---

## 🎯 Project Objectives

1. Develop an AI-powered multi-agent travel planning platform.
2. Generate personalized travel itineraries based on user requirements.
3. Coordinate specialized agents for different travel domains.
4. Optimize travel plans using budget and user constraints.
5. Incorporate contextual information such as weather, routes, ratings, and opening hours.
6. Provide an interactive AI travel assistant.
7. Support multilingual and voice-based interaction.
8. Provide community-driven travel features such as Lost & Found.
9. Demonstrate an end-to-end travel planning and mock booking workflow.

---

## 🔮 Future Scope

Potential future improvements include:

* Real-time flight and hotel availability
* Real booking integrations
* Real-time itinerary replanning
* Dynamic disruption handling
* Advanced recommendation models
* Real-time crowd information
* Personalized travel memory
* More regional language support
* Voice-first travel planning
* Mobile application
* Advanced community verification
* Real-time travel alerts

---

## ⚠️ Project Disclaimer

ATLAS is an academic/project implementation and its booking functionality is intended as a **mock booking workflow** unless explicitly connected to authorized third-party booking services.

Travel information and recommendations should be verified against authoritative sources before real-world use.

---

## 👨‍💻 Development

ATLAS is being developed as a collaborative software project using Git and GitHub.

Development follows a modular architecture so frontend, backend, AI agents, integrations, and database components can be developed independently and integrated progressively.

---

## 📄 License

This project is currently intended for academic and educational purposes.

A formal open-source license can be added if the project is later released publicly.
