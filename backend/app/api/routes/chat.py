"""
Chat route — POST /api/chat
"""
import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.core.rate_limit import ai_rate_limiter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.gemini_service import GeminiQuotaExceededError
from app.services.gemini_service import chat as gemini_chat

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the ATLAS AI travel assistant",
)
async def chat_endpoint(body: ChatRequest, request: Request) -> ChatResponse:
    """
    Accepts a user message and returns a Gemini-generated travel assistant response.

    - Input is validated by Pydantic (non-empty, max 4000 chars).
    - All Gemini logic lives in `app.services.gemini_service`.
    - Errors from Gemini are caught and returned as a safe 502 response.
    """
    await ai_rate_limiter.enforce(request, scope="chat", limit=8, window_seconds=60)
    message = body.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    try:
        reply = await gemini_chat(message)
    except GeminiQuotaExceededError as exc:
        # Gemini's own free-tier quota, not ATLAS's rate limiter — a distinct
        # 429 so the client can tell "you're going too fast" apart from
        # "the AI provider's daily/per-minute quota is exhausted."
        logger.warning("Gemini quota exhausted for chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The AI provider's free-tier quota is exhausted right now. Please try again shortly.",
            headers={"Retry-After": "60"},
        ) from exc
    except RuntimeError as exc:
        # Missing API key — configuration error, not user error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please contact the administrator.",
        ) from exc
    except Exception as exc:
        # Gemini API error, network issue, etc.
        # Log server-side for diagnosis; do NOT expose internal details to the client.
        logger.warning("Gemini chat request failed: %s: %s", type(exc).__name__, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service returned an error. Please try again in a moment.",
        )

    return ChatResponse(response=reply)
