"""One SDK/provider per process; W3C propagation across service boundaries."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langfuse import Langfuse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.settings import get_settings

propagator = TraceContextTextMapPropagator()


def setup_tracing(service_name: str) -> Langfuse:
    settings = get_settings()
    provider = trace.get_tracer_provider()
    if isinstance(provider, trace.ProxyTracerProvider):
        provider = TracerProvider(resource=Resource.create({
            "service.name": settings.otel_service_name or service_name,
        }))
        trace.set_tracer_provider(provider)
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        base_url=str(settings.langfuse_base_url).rstrip("/"),
        tracing_enabled=settings.langfuse_tracing_enabled,
        environment=settings.langfuse_tracing_environment,
        tracer_provider=provider,
        should_export_span=lambda span: True,
    )


def create_app(title: str, service_name: str) -> FastAPI:
    client = setup_tracing(service_name)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            client.shutdown()

    app = FastAPI(title=title, lifespan=lifespan)
    FastAPIInstrumentor.instrument_app(
        app, tracer_provider=trace.get_tracer_provider(),
        excluded_urls="health", http_capture_headers_server_request=[],
    )

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


def outbound_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    propagator.inject(headers)
    return headers
