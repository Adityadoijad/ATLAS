import asyncio
from dataclasses import dataclass

from app.schemas.planner import GeneratedTripPlanSchema, PlannerRequest
from app.services.agents import FoodAgent, HotelAgent, RouteAgent, WeatherAgent
from app.services.planner_service import generate_trip_plan as generate_ai_trip_plan


@dataclass
class PlannerResult:
    plan: GeneratedTripPlanSchema
    data_context: dict[str, object]


# Most integrations answer in well under a second. An agent that talks to a
# slower service (Overpass) declares its own budget via `timeout_seconds`.
# Agents run concurrently with AI plan generation, which takes several seconds
# anyway, so a longer agent budget does not lengthen the overall request.
_DEFAULT_AGENT_TIMEOUT = 2.5


async def _run_agent(agent: object, request: PlannerRequest) -> tuple[str, dict[str, object]]:
    name = getattr(agent, "name")
    timeout = getattr(agent, "timeout_seconds", _DEFAULT_AGENT_TIMEOUT)
    try:
        result = await asyncio.wait_for(agent.run(request), timeout=timeout)
        return name, result
    except asyncio.TimeoutError:
        return name, {
            "is_realtime_data": False,
            "fallback_reason": f"TimeoutError: agent timed out after {timeout} seconds",
        }
    except Exception as exc:
        return name, {
            "is_realtime_data": False,
            "fallback_reason": f"{type(exc).__name__}: agent failed",
        }


async def generate_trip_plan(request: PlannerRequest) -> PlannerResult:
    agents = [RouteAgent(), HotelAgent(), FoodAgent(), WeatherAgent()]
    plan_task = asyncio.create_task(generate_ai_trip_plan(request))
    agent_results = await asyncio.gather(*(_run_agent(agent, request) for agent in agents))
    plan = await plan_task
    context = dict(agent_results)
    context["planner"] = (
        {"is_realtime_data": True}
        if plan.is_realtime_data
        else {"is_realtime_data": False, "fallback_reason": plan.fallback_reason}
    )
    context["is_realtime_data"] = plan.is_realtime_data and all(
        result.get("is_realtime_data", False) for _, result in agent_results
    )
    return PlannerResult(plan=plan, data_context=context)
