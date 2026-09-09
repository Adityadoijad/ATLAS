import asyncio
from dataclasses import dataclass

from app.schemas.planner import GeneratedTripPlanSchema, PlannerRequest
from app.services.agents import FoodAgent, HotelAgent, RouteAgent, WeatherAgent
from app.services.planner_service import generate_trip_plan as generate_gemini_trip_plan


@dataclass
class PlannerResult:
    plan: GeneratedTripPlanSchema
    data_context: dict[str, object]


async def _run_agent(agent: object, request: PlannerRequest) -> tuple[str, dict[str, object]]:
    name = getattr(agent, "name")
    try:
        result = await asyncio.wait_for(agent.run(request), timeout=2.5)
        return name, result
    except asyncio.TimeoutError:
        return name, {
            "is_realtime_data": False,
            "fallback_reason": "TimeoutError: agent timed out after 2.5 seconds",
        }
    except Exception as exc:
        return name, {
            "is_realtime_data": False,
            "fallback_reason": f"{type(exc).__name__}: agent failed",
        }


async def generate_trip_plan(request: PlannerRequest) -> PlannerResult:
    agents = [RouteAgent(), HotelAgent(), FoodAgent(), WeatherAgent()]
    plan_task = asyncio.create_task(generate_gemini_trip_plan(request))
    agent_results = await asyncio.gather(*(_run_agent(agent, request) for agent in agents))
    plan = await plan_task
    context = dict(agent_results)
    context["is_realtime_data"] = all(result.get("is_realtime_data", False) for _, result in agent_results)
    return PlannerResult(plan=plan, data_context=context)
