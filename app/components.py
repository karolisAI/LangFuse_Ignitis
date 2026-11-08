"""Synthetic components inspired by the team's decorator example.

Do not treat keyword matching as a production security guardrail.
Payload capture is disabled to avoid recording customer messages by default.
"""
from langfuse import get_client, observe


@observe(name="input-validator", as_type="guardrail", capture_input=False, capture_output=False)
async def validate_payload(text: str) -> bool:
    is_valid = bool(text.strip()) and "drop table" not in text.lower()
    if not is_valid:
        get_client().update_current_span(level="WARNING", status_message="Blocked input")
    return is_valid


class KnowledgeRetriever:
    @observe(name="vector-db-lookup", as_type="retriever", capture_input=False, capture_output=False)
    async def fetch_chunks(self, query: str, top_k: int = 3) -> list[dict]:
        results = [{"id": "demo-billing-faq", "text": "Demo: review invoice and meter readings."}]
        results = results[:top_k]
        get_client().update_current_span(metadata={"db": "synthetic", "hits": len(results)})
        return results


@observe(name="billing-lookup", as_type="tool", capture_input=False, capture_output=False)
async def get_customer_tier(user_id: str) -> str:
    return "synthetic-residential"
