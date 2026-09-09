import httpx

from app.services.integrations.circuit_breaker import CircuitBreaker

maps_breaker = CircuitBreaker()


async def geocode_destination(destination: str) -> dict[str, float]:
    async def request_geocode() -> dict[str, float]:
        async with httpx.AsyncClient(timeout=4.0, headers={"User-Agent": "ATLAS-Travel-Planning/1.0"}) as client:
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
