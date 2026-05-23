# Actor Searcher v2

AI casting agent per un singolo attore. Monitora fonti di casting (web, Backstage, Gmail), valuta i listing semanticamente contro il profilo dell'attore, e notifica via Telegram con inline keyboard HITL.

## Quickstart

Vedere **[STARTUP.md](STARTUP.md)** per la guida completa.

```bash
cp .env.example .env
# Compilare .env + actor_profile.yaml
docker compose up --build -d
docker compose exec app alembic upgrade head
docker compose restart app
```

Il bot Telegram inizia a inviare listing al primo run (default: ogni 6 ore).

## Architettura

```
[Fonti]                [Pipeline]                    [Output]
Tavily/Brave  ──┐
Backstage     ──┼──▶ QueryGeneratorAgent
Gmail/IMAP    ──┘        ↓
                    SearchAgent (MultiProvider)
                         ↓
                    DedupAgent
                         ↓
                    DeadlineExtractorAgent
                         ↓
                    ProfileMatchingAgent  ←── ActorProfile (YAML + DB delta)
                         ↓
                    TelegramBotNotifier (inline keyboard HITL)
                         ↓
                    FeedbackRepository → PreferenceLearner (settimanale)
                                                ↓
                                        Admin Dashboard (/admin/*)
```

## Stack

Python 3.12 · FastAPI · SQLAlchemy async · Alembic · APScheduler · OpenAI Responses API · python-telegram-bot · Playwright · Jinja2 · Postgres · Redis · Docker

## Struttura

```
app/
  agents/          # stateless pipeline stages
  admin/           # dashboard (routes, auth, templates)
  config/          # settings
  feedback/        # PreferenceLearner
  models/          # SQLAlchemy + Pydantic schemas
  notifications/   # Telegram bot + handler
  profile/         # ActorProfile model + ProfileLoader
  providers/       # Tavily, Backstage, Gmail, MultiProvider
  repositories/    # DB boundaries
  scheduler/       # APScheduler + auto-search creation
  services/        # LLM + SearchOrchestrator
actor_profile.yaml   # profilo base (compilare prima dell'avvio)
```

## Configurazione chiave

| Env var | Default | Descrizione |
|---|---|---|
| `OPENAI_API_KEY` | — | Obbligatorio |
| `TAVILY_API_KEY` | — | Obbligatorio |
| `TELEGRAM_BOT_TOKEN` | — | Obbligatorio per notifiche |
| `TELEGRAM_CHAT_ID` | — | Obbligatorio per notifiche |
| `TELEGRAM_ENABLED` | `false` | Abilitare per ricevere notifiche |
| `SEARCH_INTERVAL_MINUTES` | `360` | Frequenza monitoraggio |
| `MINIMUM_MATCH_SCORE` | `0.3` | Soglia score per notifica (0–1) |
| `ADMIN_PASSWORD` | — | Password dashboard admin |

## Admin Dashboard

`http://localhost:8000/admin/profile` — gestione profilo, skill delta, suggerimenti AI, statistiche feedback.

## Sviluppo

```bash
pip install -e .[dev]
pytest
ruff check app/
mypy app/
```

## Documentazione

- [STARTUP.md](STARTUP.md) — guida completa all'avvio
- [docs/business-plan-cost-analysis.md](docs/business-plan-cost-analysis.md) — analisi costi e sostenibilità
- [docs/superpowers/specs/](docs/superpowers/specs/) — specifiche di design
- [docs/superpowers/plans/](docs/superpowers/plans/) — piani di implementazione
