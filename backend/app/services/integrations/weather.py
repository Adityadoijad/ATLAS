import httpx

from app.core.config import settings
from app.services.integrations.circuit_breaker import CircuitBreaker

weather_breaker = CircuitBreaker()


async def get_weather(destination: str) -> dict[str, object]:
    if not settings.OPENWEATHER_API_KEY:
        raise RuntimeError("OpenWeatherMap is not configured")

    async def request_weather() -> dict[str, object]:
        async with httpx.AsyncClient(timeout=4.0) as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": destination, "appid": settings.OPENWEATHER_API_KEY, "units": "metric"},
            )
            response.raise_for_status()
            payload = response.json()
            return {
                "temperature_c": payload["main"]["temp"],
                "condition": payload["weather"][0]["description"],
            }

    return await weather_breaker.call(request_weather)
