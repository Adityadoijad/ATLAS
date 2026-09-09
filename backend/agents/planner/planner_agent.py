import asyncio

from backend.route.route_agent import RouteAgent
from backend.hotel.hotel_agent import HotelAgent
from backend.food.food_agent import FoodAgent
from backend.weather.weather_agent import WeatherAgent


class PlannerAgent:
    def __init__(self):
        self.name = "ATLAS Planner Agent"

        # Initialize child agents
        self.route_agent = RouteAgent()
        self.hotel_agent = HotelAgent()
        self.food_agent = FoodAgent()
        self.weather_agent = WeatherAgent()

    async def create_itinerary(self, user_request):
        """
        Coordinates multiple child agents
        to create a travel plan.
        """

        if not user_request or not user_request.strip():
            return {
                "status": "error",
                "message": "Please provide a travel request."
            }

        # For now, use the user request as destination.
        # More advanced AI-based extraction will be added later.
        destination = user_request

        # Call all child agents in parallel
        route_result, hotel_result, food_result, weather_result = await asyncio.gather(
            self.route_agent.find_route(destination),
            self.hotel_agent.find_hotels(destination),
            self.food_agent.find_food(destination),
            self.weather_agent.get_weather(destination)
        )

        # Combine all agent results
        plan = {
            "request": user_request,
            "route": route_result,
            "hotel": hotel_result,
            "food": food_result,
            "weather": weather_result
        }

        return {
            "status": "success",
            "plan": plan
        }