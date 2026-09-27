import logging

import httpx

from app.services.integrations.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

maps_breaker = CircuitBreaker()

# Shared User-Agent string matching what the rest of the integrations use.
_USER_AGENT = "ATLAS-Travel-Planning/1.0 (https://github.com/Adityadoijad/ATLAS; student project)"


async def geocode_destination(destination: str) -> dict[str, float]:
    async def request_geocode() -> dict[str, float]:
        async with httpx.AsyncClient(timeout=4.0, headers={"User-Agent": _USER_AGENT}) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": destination, "format": "jsonv2", "limit": 1},
            )
            response.raise_for_status()
            results = response.json()
            if not results:
                raise LookupError("Destination was not found")
            return {"latitude": float(results[0]["lat"]), "longitude": float(results[0]["lon"])}

    return await maps_breaker.call(request_geocode)


async def validate_india_destination(
    name: str, state: str
) -> dict[str, object] | None:
    """Validate that a Groq-suggested destination actually exists in India.

    Queries Nominatim with "{name}, {state}, India" and confirms the result's
    country_code is "in".  Returns a dict with validated lat/lon/display_name,
    or None when the place cannot be confirmed (not found, not India, or any
    network/service error).

    Never raises — callers discard None results silently so a single bad
    Groq suggestion cannot abort the whole recommendation batch.
    """
    query = f"{name}, {state}, India"
    try:
        async def _request() -> dict[str, object] | None:
            async with httpx.AsyncClient(
                timeout=6.0, headers={"User-Agent": _USER_AGENT}, follow_redirects=True
            ) as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "limit": 3,
                        "countrycodes": "in",  # Pre-filter at the API level
                        "addressdetails": 1,
                    },
                )
                response.raise_for_status()
                results = response.json()
                if not results:
                    return None
                # Take the first result with country_code == "in" as a double-
                # check, since the countrycodes param can still return nearby
                # border results for poorly geocoded names.
                for result in results:
                    if (result.get("address") or {}).get("country_code", "").lower() == "in":
                        return {
                            "latitude": float(result["lat"]),
                            "longitude": float(result["lon"]),
                            "display_name": result.get("display_name", query),
                        }
                return None

        return await maps_breaker.call(_request)
    except Exception as exc:
        logger.warning("India destination validation failed for %r: %s", query, type(exc).__name__)
        return None

