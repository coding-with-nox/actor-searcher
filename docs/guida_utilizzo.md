# Guida all'utilizzo di Actor Searcher

Questa guida spiega come avviare, configurare e usare la piattaforma **Actor Searcher** per monitorare ricerche web periodiche con ranking e sintesi AI.

## 1) Prerequisiti

- Docker e Docker Compose installati
- Chiavi API valide:
  - OpenAI (`OPENAI_API_KEY`)
  - Tavily (`TAVILY_API_KEY`)

## 2) Configurazione ambiente

1. Copia il file di esempio:

```bash
cp .env.example .env
```

2. Aggiorna `.env` con i valori reali, almeno:

- `OPENAI_API_KEY`
- `TAVILY_API_KEY`
- (opzionale) `OPENAI_MODEL`

## 3) Avvio rapido con Docker

```bash
docker compose up --build
```

L'API sarà disponibile su `http://localhost:8000`.

Documentazione Swagger: `http://localhost:8000/docs`.

## 4) Migrazioni database

In un terminale separato (con container attivi), esegui:

```bash
docker compose exec app alembic upgrade head
```

Questo crea le tabelle:

- `searches`
- `search_runs`
- `search_results`
- `notifications`

## 5) Flusso operativo

Ad ogni intervallo configurato:

1. lo scheduler seleziona le ricerche abilitate;
2. il provider esegue le query web;
3. il ranking AI assegna uno score;
4. la sintesi AI genera summary brevi;
5. il dedup rimuove risultati duplicati;
6. i risultati vengono salvati su PostgreSQL.

## 6) API principali

Base path: `/api/v1`

### Healthcheck

```http
GET /api/v1/health
```

### Creazione ricerca

```http
POST /api/v1/searches
Content-Type: application/json

{
  "name": "ai-architecture",
  "interval_minutes": 15,
  "config": {
    "queries": [
      "AI software architecture",
      "multi-agent systems",
      "LLM orchestration"
    ],
    "scoring": {
      "keywords": ["observability", "orchestration", "memory"],
      "minimum_score": 0.75
    }
  }
}
```

### Elenco ricerche

```http
GET /api/v1/searches
```

### Elenco run

```http
GET /api/v1/runs
```

### Elenco risultati

```http
GET /api/v1/results
```

## 7) Esecuzione locale senza Docker (sviluppo)

```bash
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

> Assicurati che PostgreSQL e Redis siano raggiungibili con gli URL configurati.

## 8) Test e qualità

```bash
pytest
ruff check .
mypy app
```

## 9) Troubleshooting rapido

- **Errore API key**: verifica `.env`.
- **Scheduler non parte**: controlla i log in output JSON.
- **Nessun risultato**: riduci `minimum_score` o amplia le query.
- **Errori DB**: assicurati di aver eseguito `alembic upgrade head`.

## 10) Buone pratiche operative

- Inizia con poche query e intervallo >= 15 minuti.
- Definisci keyword di scoring specifiche per ridurre rumore.
- Monitora periodicamente i risultati salvati per tarare il ranking.
