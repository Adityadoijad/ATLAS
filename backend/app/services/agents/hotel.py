from app.schemas.planner import PlannerRequest


class HotelAgent:
    name = "hotel"

    async def run(self, request: PlannerRequest) -> dict[str, object]:
        nights = max(1, (request.end_date - request.start_date).days)
        nightly_budget = round(request.budget * 0.35 / nights, 2)
        return {
            "is_realtime_data": False,
            "recommendation": f"Target accommodation near the city centre at about {nightly_budget} {request.currency} per night.",
            "fallback_reason": "Estimated from trip budget; live inventory is not connected.",
        }
