# LangFuse_Ignitis

Self-hosted Langfuse tracing across FastAPI services and Google ADK agents.
Includes a synthetic energy-support flow with guardrail, retrieval and billing spans.

The [architecture walkthrough](ARCHITECTURE.md) explains the request flow, trace
propagation, ingestion pipeline, dependencies and remaining integration work.
This is a reference implementation; the actual Ignitis services are not connected.

## Setup

Requires Python 3.11–3.13, [uv](https://docs.astral.sh/uv/) and Docker running.
For a fresh checkout:

```powershell
git clone https://github.com/karolisAI/LangFuse_Ignitis.git
cd LangFuse_Ignitis
uv sync --locked --all-extras
uv run python scripts/setup_langfuse.py
docker compose --project-directory infra/.runtime -f infra/.runtime/compose.yaml up -d langfuse-web langfuse-worker
Copy-Item .env.example .env
```

Open http://localhost:3000, sign up, create a project and copy its keys into `.env`
as `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`.
Keep `LANGFUSE_BASE_URL=http://localhost:3000`.

Start services in separate terminals:

```powershell
# Terminal 1
$env:OTEL_SERVICE_NAME='ignitis-specialist'
uv run python -m uvicorn app.specialist:app --host 127.0.0.1 --port 8001
```

```powershell
# Terminal 2
$env:OTEL_SERVICE_NAME='ignitis-gateway'
uv run python -m uvicorn app.gateway:app --host 127.0.0.1 --port 8000
```

Send a request:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/chat -Method Post -ContentType application/json -Body '{"message":"How can I check my energy invoice?"}'
```

Find the returned `trace_id` in Langfuse. Allow a few seconds for ingestion.
The trace links `chat-orchestrator`, `input-validator`, `energy-specialist`,
`vector-db-lookup` and `billing-lookup` across both services.
Send `"drop table"` to see a validator warning; stop the specialist to see a dependency error.

## Wire into existing services

- Initialize Langfuse once per process with your project keys and self-hosted URL.
- Use `app/telemetry.py` to instrument FastAPI with the same OTel provider as Langfuse.
- Add `@observe` to components, following `app/components.py`.
- Forward W3C trace context using `outbound_headers()` on downstream calls.
- Set `OTEL_SERVICE_NAME` per service. Use `propagate_attributes` with approved,
  pseudonymous user/session IDs to group conversation turns.

The service demo uses synthetic responses and disables prompt/result capture.
The keyword validator is only a demonstration; no real billing system is connected.
Each request gets a fresh synthetic session; replace it with your conversation ID.

## ADK

Set `GOOGLE_API_KEY` and an available `ADK_MODEL` in `.env`, then run:

```powershell
uv run python examples/adk_demo.py
```

This runs a root agent with a billing sub-agent and the OpenInference ADK instrumentor.
It captures model payloads: use synthetic data until redaction is configured.
Model calls may incur charges. Delegation depends on the model's response.

## Checks and shutdown

```powershell
uv run ruff check .
uv run python -m pytest -q
docker compose --project-directory infra/.runtime -f infra/.runtime/compose.yaml down
```

Tests check local spans, cross-service propagation, isolation and failures.
Backend ingestion and real-model calls require a running Langfuse instance and keys.
Compose pins Langfuse 4.76.0 and generates gitignored secrets. Add TLS, access controls
and backups before shared deployment. Actual project integration and evaluations remain open.

References: [Langfuse](https://github.com/langfuse/langfuse),
[self-hosting](https://langfuse.com/self-hosting/deployment/docker-compose),
[ADK](https://adk.dev/),
[ADK tracing](https://langfuse.com/integrations/frameworks/google-adk).
