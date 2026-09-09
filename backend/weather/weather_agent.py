class WeatherAgent:
    def __init__(self):
        self.name = "ATLAS Weather Agent"

    async def get_weather(self, destination):
        return {
            "destination": destination,
            "weather": "Pleasant weather expected",
            "status": "success"
        }