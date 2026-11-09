"""Optional real-model example; requires a Google API key and local Langfuse keys."""
import asyncio
from uuid import uuid4

from langfuse import propagate_attributes

from app.settings import get_settings
from app.telemetry import setup_tracing


async def main():
    from google.adk.agents import Agent
    from google.adk.models.google_llm import Gemini
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor
    from opentelemetry import trace

    settings = get_settings()
    if not settings.google_api_key.get_secret_value():
        raise SystemExit("Set GOOGLE_API_KEY for the optional real-model demo.")
    client = setup_tracing("ignitis-adk")
    if not client.auth_check():
        raise SystemExit("Check self-hosted Langfuse URL and project keys.")
    GoogleADKInstrumentor().instrument(tracer_provider=trace.get_tracer_provider())
    # Synthetic prompt only: ADK's instrumentor captures model/tool payloads.
    model = Gemini(
        model=settings.adk_model,
        client_kwargs={"api_key": settings.google_api_key.get_secret_value(), "vertexai": False},
    )
    specialist = Agent(
        name="billing_specialist", model=model,
        description="Handles demonstration energy billing questions.",
        instruction="Explain how to compare an invoice with meter readings. Never invent tariffs.",
    )
    root = Agent(
        name="energy_support", model=model, sub_agents=[specialist],
        instruction="Delegate energy invoice questions to billing_specialist.",
    )
    sessions = InMemorySessionService()
    session_id = str(uuid4())
    await sessions.create_session(app_name="ignitis_demo", user_id="synthetic", session_id=session_id)
    runner = Runner(agent=root, app_name="ignitis_demo", session_service=sessions)
    try:
        with (
            propagate_attributes(session_id=session_id, tags=["synthetic", "adk"]),
            client.start_as_current_observation(name="adk-energy-chat", as_type="agent"),
        ):
            async for event in runner.run_async(
                user_id="synthetic", session_id=session_id,
                new_message=types.Content(role="user", parts=[types.Part(
                    text="How do I check a demonstration energy invoice?"
                )]),
            ):
                if event.is_final_response() and event.content:
                    print("".join(part.text or "" for part in event.content.parts or []))
            print("Trace:", client.get_trace_url())
    finally:
        client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
