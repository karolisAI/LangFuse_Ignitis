import os
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from langfuse import get_client, observe, propagate_attributes
from pydantic import BaseModel, Field

from app.components import validate_payload
from app.telemetry import instrument, lifespan, outbound_headers

app = FastAPI(title="Ignitis telemetry PoC", lifespan=lifespan)
instrument(app)


class ChatRequest(BaseModel):
    message: str = Field(max_length=4000)


@observe(name="chat-orchestrator", as_type="agent", capture_input=False, capture_output=False)
async def orchestrate(message: str):
    if not await validate_payload(message):
        raise HTTPException(422, "Input rejected by demonstration validator")
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(
                os.getenv("SPECIALIST_URL", "http://127.0.0.1:8001") + "/answer",
                json={"message": message}, headers=outbound_headers(),
            )
            response.raise_for_status()
        except httpx.HTTPError:
            # Avoid exception details that can include response bodies/customer data.
            get_client().update_current_span(level="ERROR", status_message="Specialist unavailable")
            raise HTTPException(502, "Specialist unavailable") from None
    result = response.json()
    return {**result, "trace_id": get_client().get_current_trace_id()}


@app.post("/chat")
async def chat(payload: ChatRequest):
    with propagate_attributes(session_id=str(uuid4()), tags=["synthetic", "energy-support"]):
        return await orchestrate(payload.message)


@app.get("/health")
async def health():
    return {"status": "ok"}
