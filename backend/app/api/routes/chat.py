"""
Chat route — POST /api/chat
"""
import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.core.rate_limit import ai_rate_limiter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai_service import AIConfigurationError, AIQuotaExceededError
from app.services.chat_service import chat as ai_chat

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the ATLAS AI travel assistant",
)
async def chat_endpoint(body: ChatRequest, request: Request) -> ChatResponse:
    """
    Accepts a user message and returns an AI-generated travel assistant response.

    - Input is validated by Pydantic (non-empty, max 4000 chars).
    - All provider logic lives in `app.services.ai_service`.
    - Upstream failures are mapped to safe HTTP responses.
    """
    await ai_rate_limiter.enforce(request, scope="chat", limit=8, window_seconds=60)
    message = body.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    try:
        reply = await ai_chat(message)
    except AIQuotaExceededError as exc:
        # The provider's own quota, not ATLAS's rate limiter — a distinct 429
        # so the client can tell "you're going too fast" apart from "the AI
        # provider's quota is exhausted."
        logger.warning("AI provider quota exhausted for chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI provider's quota is exhausted right now. Please try again shortly.",
            headers={"Retry-After": "60"},
        ) from exc
    except AIConfigurationError as exc:
        # Missing/invalid API key — configuration error, not user error
        logger.error("AI provider misconfigured for chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please contact the administrator.",
        ) from exc
    except Exception as exc:
        # Provider error, network issue, etc.
        # Log server-side for diagnosis; do NOT expose internal details to the client.
        logger.warning("AI chat request failed: %s: %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service returned an error. Please try again in a moment.",
        )

    return ChatResponse(response=reply)
