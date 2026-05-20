# Actor Searcher
Production-grade async backend for scheduled AI-assisted web intelligence.

## Features
- FastAPI API for search configs, runs, and results
- APScheduler-based recurring execution
- Provider abstraction (Tavily + Brave)
- LLM ranking/summarization via OpenAI Responses API
- Dedup (URL + content hash)
- Postgres persistence + Alembic migrations
- Structlog JSON logging

## Quickstart
1. `cp .env.example .env`
2. `docker compose up --build`
3. `alembic upgrade head`
4. Open `http://localhost:8000/docs`

## Env vars
- `DATABASE_URL`
- `REDIS_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `TAVILY_API_KEY`
- `BRAVE_API_KEY`

## Development
- `pip install -e .[dev]`
- `pytest`
- `ruff check .`
- `mypy app`

## Architecture
- `app/agents`: stateless execution stages
- `app/providers`: interchangeable search providers
- `app/services`: orchestration + LLM integration
- `app/repositories`: DB persistence boundaries
- `app/scheduler`: recurring job registration and lifecycle
- `app/notifications`: pluggable channels

## Extensibility
- Add providers by implementing `SearchProvider`
- Add notification channels via `NotificationChannel`
- Add specialized agents as pure async components

## Troubleshooting
- Ensure API keys are set
- Ensure migrations have run
- Check JSON logs for correlation fields
