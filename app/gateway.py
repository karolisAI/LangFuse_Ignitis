from uuid import uuid4

import httpx
from fastapi import HTTPException
from langfuse import get_client, observe, propagate_attributes

from app.components import validate_payload
from app.models import ChatRequest, ChatResponse
from app.settings import get_settings
from app.telemetry import create_app, outbound_headers

app = create_app("Ignitis telemetry demo", "ignitis-gateway")
settings = get_settings()


@observe(name="chat-orchestrator", as_type="agent", capture_input=False, capture_output=False)
async def orchestrate(message: str) -> ChatResponse:
    if not await validate_payload(message):
        raise HTTPException(422, "Input rejected by demonstration validator")
    async with httpx.AsyncClient(timeout=settings.specialist_timeout_seconds) as client:
        try:
            response = await client.post(
                str(settings.specialist_url).rstrip("/") + "/answer",
                json={"message": message}, headers=outbound_headers(),
            )
            response.raise_for_status()
            result = ChatResponse.model_validate(response.json())
        except (httpx.HTTPError, ValueError):
            # Avoid exception details that can include response bodies/customer data.
            get_client().update_current_span(level="ERROR", status_message="Specialist unavailable")
            raise HTTPException(502, "Specialist unavailable") from None
    return ChatResponse(answer=result.answer, trace_id=get_client().get_current_trace_id())


@app.post("/chat")
async def chat(payload: ChatRequest) -> ChatResponse:
    with propagate_attributes(session_id=str(uuid4()), tags=["synthetic", "energy-support"]):
        return await orchestrate(payload.message)
