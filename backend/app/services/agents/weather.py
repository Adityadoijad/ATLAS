from app.schemas.planner import PlannerRequest
from app.services.integrations.weather import get_weather


class WeatherAgent:
    name = "weather"

    async def run(self, request: PlannerRequest) -> dict[str, object]:
        try:
            weather = await get_weather(request.destination)
            return {"is_realtime_data": True, "forecast": weather}
        except Exception as exc:
            return {
                "is_realtime_data": False,
                "forecast": {"condition": "Check the forecast shortly before departure."},
                "fallback_reason": type(exc).__name__,
            }
