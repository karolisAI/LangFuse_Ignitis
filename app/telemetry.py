"""One SDK/provider per process; W3C propagation across service boundaries."""
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from langfuse import Langfuse, get_client
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

load_dotenv()
propagator = TraceContextTextMapPropagator()


@asynccontextmanager
async def lifespan(app):
    client = get_client()
    try:
        yield
    finally:
        client.shutdown()


def instrument(app):
    # Use the SAME provider as @observe; otherwise HTTP spans can split the trace.
    # Include HTTP spans alongside AI spans to show service boundaries.
    Langfuse(should_export_span=lambda span: True)
    FastAPIInstrumentor.instrument_app(
        app, tracer_provider=trace.get_tracer_provider(),
        excluded_urls="health", http_capture_headers_server_request=[],
    )


def outbound_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    propagator.inject(headers)
    return headers
