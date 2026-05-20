# AGENTS Instructions

## Architecture
- Keep domain models in `app/models`, persistence in `app/repositories`, infra integrations in `app/providers` and `app/notifications`.
- Maintain async-first design; no synchronous network/database calls.

## Coding Standards
- Python 3.12, strict typing, small modules, dependency injection.
- Public APIs require docstrings.
- Use `structlog`; never `print()`.

## Forbidden Patterns
- No `requests` library.
- No `while True` loops for scheduling.
- No global mutable runtime state.

## Agent Rules
- Agents must be stateless and expose async `execute()`.
- Agent responsibilities must remain isolated (search/rank/summarize/dedup/notify).

## Provider Rules
- Providers must normalize to `app.models.schemas.SearchResult`.
- Use async `httpx` with timeout and retries.
- Raise typed exceptions for retryable/non-retryable failures.

## Testing & Quality
- Run: `pytest`
- Run: `ruff check .`
- Run: `mypy app`
