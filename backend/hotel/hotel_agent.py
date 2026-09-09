class HotelAgent:
    def __init__(self):
        self.name = "ATLAS Hotel Agent"

    async def find_hotels(self, destination):
        return {
            "destination": destination,
            "hotels": [
                "Recommended Hotel 1",
                "Recommended Hotel 2"
            ],
            "status": "success"
        }