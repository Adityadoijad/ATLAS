class FoodAgent:
    def __init__(self):
        self.name = "ATLAS Food Agent"

    async def find_food(self, destination):
        return {
            "destination": destination,
            "restaurants": [
                "Recommended Restaurant 1",
                "Recommended Restaurant 2"
            ],
            "status": "success"
        }