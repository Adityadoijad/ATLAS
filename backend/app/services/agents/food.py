from app.schemas.planner import PlannerRequest


class FoodAgent:
    name = "food"

    async def run(self, request: PlannerRequest) -> dict[str, object]:
        preferences = request.preferences.get("food", [])
        preference_text = ", ".join(str(item) for item in preferences) or "local cuisine"
        return {
            "is_realtime_data": False,
            "recommendation": f"Prioritise {preference_text} and reserve roughly 16% of the budget for meals.",
            "fallback_reason": "Estimated recommendation; live restaurant availability is not connected.",
        }
