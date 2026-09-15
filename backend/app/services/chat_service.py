"""ATLAS travel-assistant chat.

Thin feature layer over the centralized AI provider in ai_service.py — this
module owns the assistant's behaviour (system instruction), not the provider.
"""
from app.core.prompts import ATLAS_SYSTEM_INSTRUCTION
from app.services.ai_service import generate


async def chat(user_message: str) -> str:
    """Send a user message to the configured AI provider and return the reply.

    Raises the provider-neutral errors from ai_service (configuration, quota,
    generation) for the route layer to map onto HTTP responses.
    """
    return await generate(user_message, system_instruction=ATLAS_SYSTEM_INSTRUCTION)
