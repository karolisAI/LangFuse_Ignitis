# LangFuse_Ignitis

Send a message. Two small services handle it. Open Langfuse to see what each one
did, how long it took, and whether anything failed.

That list of steps is called a **trace**. This project shows how to keep one trace
when a request moves from one service to another.

```text
Your message -> gateway -> specialist -> demo answer
                 |             |
                 +-> Langfuse <-+
```

The answers, knowledge lookup and billing lookup are fake. You don't need a model
key to try this. The real Ignitis chatbot is not connected yet.

## Run it

You need Python 3.11-3.13, [uv](https://docs.astral.sh/uv/), Git and Docker.
Start Docker Desktop before continuing. These commands use PowerShell.

### 1. Download the project and start Langfuse

```powershell
git clone https://github.com/karolisAI/LangFuse_Ignitis.git
cd LangFuse_Ignitis
uv sync --locked
uv run python scripts/setup_langfuse.py
docker compose --project-directory infra/.runtime -f infra/.runtime/compose.yaml up -d langfuse-web langfuse-worker
```

The setup script creates local passwords and Docker settings. Keep those files;
you can reuse them next time. The first start needs time to download the images
and prepare the databases.

### 2. Give the demo permission to send traces

Open http://localhost:3000. Sign up, create a project, then find its API keys in
the project settings.

On your first setup, copy the example settings file:

```powershell
Copy-Item .env.example .env
```

Open `.env` and fill in these two lines with your project's keys:

```dotenv
LANGFUSE_PUBLIC_KEY=your-public-key
LANGFUSE_SECRET_KEY=your-secret-key
```

Leave `LANGFUSE_BASE_URL=http://localhost:3000`. Keep `.env` out of Git.
If you already have a local account and `.env`, use those instead of creating new ones.

### 3. Start the two services

Open two terminals in the project folder. Leave them running.

In the first terminal:

```powershell
uv run python -m uvicorn app.specialist:app --host 127.0.0.1 --port 8001
```

In the second:

```powershell
uv run python -m uvicorn app.gateway:app --host 127.0.0.1 --port 8000
```

### 4. Send a message and find its trace

Open http://localhost:8000/docs. Expand **POST /chat**, click **Try it out**, and enter:

```json
{"message": "How can I check my energy invoice?"}
```

Click **Execute**. You'll get a demo answer and a `trace_id`.
Open Langfuse and find that ID. Allow a few seconds for the trace to arrive.

You should see the gateway, an input check, the specialist, a knowledge lookup
and a billing lookup. All belong to the same trace.

Try `drop table` as the message to see a blocked-input warning. Stop the specialist
and send a normal message to see what a failed service call looks like.

## What are all the Docker containers for?

| Component | Its job |
| --- | --- |
| Langfuse Web | The page you open and the API receiving traces |
| Langfuse Worker | Processes the received traces in the background |
| PostgreSQL | Stores users, projects and settings |
| Redis | Holds the work queue and cached data |
| MinIO | Stores the raw batches of trace data; the queue holds references to them |
| ClickHouse | Stores the observations so Langfuse can search and chart them |

## Where should I look in the code?

- `app/gateway.py`: receives your message and calls the specialist.
- `app/specialist.py`: runs the demo lookups and returns an answer.
- `app/components.py`: the input check and the two fake lookups.
- `app/telemetry.py`: connects both services to Langfuse and passes the trace ID along.
- `app/settings.py`: reads and checks settings from `.env` or environment variables.

To trace a real function, follow the `@observe` examples in `components.py`.
Those examples keep function inputs and outputs out of traces. Check what your
own integrations capture before sending customer messages.

The [full architecture walkthrough](ARCHITECTURE.md) explains the wiring and the
work still needed for the real system, including conversation IDs across services.

## Want to try real agents?

There's a separate Google ADK example with a main agent and a billing agent.
Set `GOOGLE_API_KEY` and a model available to your account in `ADK_MODEL`, then run:

```powershell
uv run --extra adk python -m examples.adk_demo
```

This makes real model calls and may cost money. It captures model inputs and
outputs, so start with made-up questions. It doesn't change the `/chat` demo.

## Change settings or stop it

The defaults are in `app/settings.py`. Environment variables override `.env`.
Restart the Python services after changing their settings. If you set
`OTEL_SERVICE_NAME`, it overrides the service's built-in name.

Press **Ctrl+C** in each Python terminal. To stop Langfuse and keep its data:

```powershell
docker compose --project-directory infra/.runtime -f infra/.runtime/compose.yaml down
```

To run the code checks:

```powershell
uv run ruff check .
uv run python -m pytest -q
```

This setup is for trying things locally. A shared deployment still needs access
controls, HTTPS and backups.
