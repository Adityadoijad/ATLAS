from fastapi import FastAPI
from pydantic import BaseModel

from backend.agents.planner.planner_agent import PlannerAgent

app = FastAPI(title="ATLAS API")

planner_agent = PlannerAgent()


class TravelRequest(BaseModel):
    user_request: str


@app.get("/")
def read_root():
    return {"message": "Welcome to ATLAS API"}


@app.post("/plan")
async def create_plan(request: TravelRequest):
    result = await planner_agent.create_itinerary(
        request.user_request
    )

    return result