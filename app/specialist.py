from langfuse import get_client, observe

from app.components import fetch_chunks, get_customer_tier
from app.models import ChatRequest, ChatResponse
from app.telemetry import create_app

app = create_app("Energy specialist demo", "ignitis-specialist")


@observe(name="energy-specialist", as_type="agent", capture_input=False, capture_output=False)
async def answer(message: str) -> ChatResponse:
    await fetch_chunks(message)
    await get_customer_tier("synthetic-customer")
    return ChatResponse(
        answer="Synthetic demo: compare your invoice with your meter readings.",
        trace_id=get_client().get_current_trace_id(),
    )


@app.post("/answer")
async def specialist(payload: ChatRequest) -> ChatResponse:
    return await answer(payload.message)
