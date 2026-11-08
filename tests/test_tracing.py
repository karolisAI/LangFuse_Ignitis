import asyncio

import httpx
import pytest
from conftest import client, exporter
from fastapi import HTTPException
from opentelemetry import context

from app import gateway, specialist


@pytest.fixture
def clients(monkeypatch):
    exporter.clear()
    original = httpx.AsyncClient

    class RemoteTransport(httpx.ASGITransport):
        async def handle_async_request(self, request):
            # Fresh context simulates a separate process at this HTTP boundary.
            token = context.attach(context.Context())
            try:
                return await super().handle_async_request(request)
            finally:
                context.detach(token)

    def downstream(*args, **kwargs):
        return original(*args, transport=RemoteTransport(app=specialist.app), **kwargs)

    monkeypatch.setattr(gateway.httpx, "AsyncClient", downstream)
    return original(transport=httpx.ASGITransport(app=gateway.app), base_url="http://test")


async def test_cross_service_trace_and_concurrent_isolation(clients):
    async with clients as api:
        results = await asyncio.gather(*[
            api.post("/chat", json={"message": "Demo invoice question"}) for _ in range(3)
        ])
    assert all(result.status_code == 200 for result in results)
    trace_ids = {result.json()["trace_id"] for result in results}
    assert len(trace_ids) == 3
    client.flush()
    for trace_id in trace_ids:
        spans = [s for s in exporter.get_finished_spans()
                 if f"{s.context.trace_id:032x}" == trace_id]
        assert {"chat-orchestrator", "input-validator", "energy-specialist",
                "vector-db-lookup", "billing-lookup"} <= {s.name for s in spans}
        by_id = {s.context.span_id: s for s in spans}
        agent = next(s for s in spans if s.name == "energy-specialist")
        ancestors = []
        while agent.parent and agent.parent.span_id in by_id:
            agent = by_id[agent.parent.span_id]
            ancestors.append(agent.name)
        assert "chat-orchestrator" in ancestors
        for span in spans:
            assert "Demo invoice question" not in str(dict(span.attributes))


async def test_rejected_input_records_warning(clients):
    async with clients as api:
        result = await api.post("/chat", json={"message": "drop table"})
    assert result.status_code == 422
    client.flush()
    spans = exporter.get_finished_spans()
    guardrail = next(s for s in spans if s.name == "input-validator")
    assert guardrail.attributes["langfuse.observation.level"] == "WARNING"
    assert not any(s.name == "energy-specialist" for s in spans)


async def test_downstream_failure_records_error(clients, monkeypatch):
    async def fail(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(type(clients), "post", fail)
    with pytest.raises(HTTPException) as exc:
        await gateway.orchestrate("synthetic")
    assert exc.value.status_code == 502
    client.flush()
    span = next(s for s in exporter.get_finished_spans() if s.name == "chat-orchestrator")
    assert span.attributes["langfuse.observation.level"] == "ERROR"
