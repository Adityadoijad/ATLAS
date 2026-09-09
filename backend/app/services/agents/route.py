from app.schemas.planner import PlannerRequest
from app.services.integrations.maps import geocode_destination


class RouteAgent:
    name = "route"

    async def run(self, request: PlannerRequest) -> dict[str, object]:
        try:
            coordinates = await geocode_destination(request.destination)
            return {"is_realtime_data": True, "coordinates": coordinates, "recommendation": "Use local transit and pre-book long transfers."}
        except Exception as exc:
            return {"is_realtime_data": False, "recommendation": "Allow time for local transfers; exact routing is unavailable.", "fallback_reason": type(exc).__name__}
