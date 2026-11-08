from fastapi import FastAPI
from langfuse import get_client, observe
from pydantic import BaseModel, Field

from app.components import KnowledgeRetriever, get_customer_tier
from app.telemetry import instrument, lifespan

app = FastAPI(title="Synthetic energy specialist", lifespan=lifespan)
instrument(app)


class SpecialistRequest(BaseModel):
    message: str = Field(max_length=4000)


@observe(name="energy-specialist", as_type="agent", capture_input=False, capture_output=False)
async def answer(message: str):
    await KnowledgeRetriever().fetch_chunks(message)
    await get_customer_tier("synthetic-customer")
    return {"answer": "Synthetic demo: compare your invoice with your meter readings.",
            "trace_id": get_client().get_current_trace_id()}


@app.post("/answer")
async def specialist(payload: SpecialistRequest):
    return await answer(payload.message)


@app.get("/health")
async def health():
    return {"status": "ok"}
