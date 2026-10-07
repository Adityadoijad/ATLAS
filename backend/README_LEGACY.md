# Legacy prototype agents — not used

`food/`, `hotel/`, `route/`, `weather/` and `agents/planner/` hold the original
Phase-1 agent stubs. They are **dead code** and must not be revived.

Each returns fabricated data:

| File | Returns |
|---|---|
| `food/food_agent.py` | `"Recommended Restaurant 1"`, `"Recommended Restaurant 2"` |
| `hotel/hotel_agent.py` | `"Recommended Hotel 1"`, `"Recommended Hotel 2"` |
| `route/route_agent.py` | `f"Best route to {destination}"` |
| `weather/weather_agent.py` | `"Pleasant weather expected"` |

`agents/planner/planner_agent.py` imports them via `from backend.X import ...`,
which does not resolve from any entry point in this project, so none of it can
execute.

The live agents are in **`app/services/agents/`** and are backed by real
providers: OpenStreetMap/Overpass (food), OSRM + Nominatim (route),
OpenWeatherMap (weather). `HotelAgent` there has no live inventory provider and
says so explicitly via `is_realtime_data: False` and a `fallback_reason`.

These files are kept only as project history. Nothing should import them.
