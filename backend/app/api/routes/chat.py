"""
Chat route — POST /api/chat
"""
from fastapi import APIRouter, HTTPException, Request, status

from app.core.rate_limit import ai_rate_limiter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.gemini_service import chat as gemini_chat

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
    await ai_rate_limiter.enforce(request, scope="chat", limit=20, window_seconds=60)
    message = body.message.strip()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    try:
        reply = await gemini_chat(message)
    except RuntimeError as exc:
        # Missing API key — configuration error, not user error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured. Please contact the administrator.",
        ) from exc
    except Exception:
        # Gemini API error, network issue, etc.
        # Do NOT expose internal details to the client.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service returned an error. Please try again in a moment.",
        )

    return ChatResponse(response=reply)
