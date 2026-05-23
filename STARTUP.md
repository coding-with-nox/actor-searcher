# Actor Searcher v2 — Guida all'avvio

Questa guida copre tutto il necessario per avviare il sistema dalla prima configurazione fino alla prima notifica Telegram.

---

## Prerequisiti

- Docker Desktop installato e avviato
- Account Telegram (per ricevere notifiche)
- Chiavi API:
  - [OpenAI](https://platform.openai.com/api-keys) — modello `gpt-4.1-mini`
  - [Tavily](https://app.tavily.com) — piano Starter (~$9/mese) o Free (600 ricerche/mese)

---

## 1. Configurazione iniziale

### 1a. Variabili d'ambiente

```bash
cp .env.example .env
```

Aprire `.env` e compilare almeno questi campi:

```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

TELEGRAM_BOT_TOKEN=...      # da @BotFather su Telegram
TELEGRAM_CHAT_ID=...        # il tuo ID numerico (da @userinfobot)
TELEGRAM_ENABLED=true

ADMIN_USERNAME=admin
ADMIN_PASSWORD=scegli_una_password_sicura

SEARCH_INTERVAL_MINUTES=360  # ogni 6 ore (default)
```

#### Come ottenere TELEGRAM_BOT_TOKEN
1. Aprire Telegram → cercare `@BotFather`
2. Inviare `/newbot` e seguire le istruzioni
3. Copiare il token fornito

#### Come ottenere TELEGRAM_CHAT_ID
1. Cercare `@userinfobot` su Telegram
2. Inviare `/start`
3. Copiare il valore `Id:` che appare

### 1b. Profilo attore

Aprire `actor_profile.yaml` e compilarlo:

```yaml
name: "Mario Rossi"
age: 28
gender: male
languages:
  - "Italian (native)"
  - "English (C1)"
physical:
  height_cm: 180
  build: athletic          # slim / athletic / average / heavy
  hair_color: brown
  eye_color: green
skills:
  - singing
  - dancing
experience_level: emerging  # emerging / mid / established
union_status: non-union     # non-union / Equity / SAG-AFTRA
location: Roma
max_travel_km: 200
availability_from: "2026-06-01"  # ISO date
```

> **Nota:** Le skill dinamiche (acquisite nel tempo) si aggiungono tramite la dashboard admin, non modificando questo file.

---

## 2. Avvio con Docker

```bash
docker compose up --build -d
```

Attendi che tutti i container siano `healthy`:

```bash
docker compose ps
```

Output atteso:
```
NAME                STATUS
actor-searcher-app  Up (healthy)
actor-searcher-postgres  Up (healthy)
actor-searcher-redis     Up
```

---

## 3. Migrazione database

Al primo avvio eseguire una sola volta:

```bash
docker compose exec app alembic upgrade head
```

Output atteso:
```
Running upgrade  -> 0001, initial schema
Running upgrade 0001 -> 0002, actor profile tables
```

> Riavviare il container dopo la migrazione:
> ```bash
> docker compose restart app
> ```

Al riavvio lo scheduler crea automaticamente la search `casting-monitor` e parte il monitoraggio.

---

## 4. Verifica funzionamento

### Healthcheck API
```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok"}
```

### Dashboard admin
Aprire `http://localhost:8000/admin/profile`
- Username: valore di `ADMIN_USERNAME`
- Password: valore di `ADMIN_PASSWORD`

### Log in tempo reale
```bash
docker compose logs -f app
```

Dopo il primo run vedrai righe come:
```json
{"event": "orchestrator.queries_generated", "count": 10}
{"event": "orchestrator.deduped", "count": 45}
{"event": "orchestrator.ranked", "count": 12}
{"event": "telegram.listing_sent", "result_id": 1, "score": 0.87}
```

---

## 5. Usare il bot Telegram

Quando arriva un listing, il bot invia un messaggio come questo:

```
🎭 Protagonista — Thriller psicologico
📍 BACKSTAGE | Score: 0.87 | Categoria: thriller | Scadenza: 30 mag

"Profilo compatibile: età e fisico corrispondono.
Red flags: richiesto patente B (non in profilo)"

🔗 https://www.backstage.com/listing/...

[✅ Invia CV] [⭐ Salva] [❌ Ignora]
```

| Pulsante | Azione |
|---|---|
| ✅ Invia CV | Segna come approvato — apri il link e candidati |
| ⭐ Salva | Tieni da parte per dopo |
| ❌ Ignora | Scarta — il sistema impara che questo tipo non interessa |

### Comandi bot

| Comando | Funzione |
|---|---|
| `/profile` | Mostra il profilo corrente |
| `/stats` | Statistiche feedback per categoria |

---

## 6. Dashboard admin

`http://localhost:8000/admin/`

| Pagina | URL | Funzione |
|---|---|---|
| Profilo | `/admin/profile` | Visualizza profilo, aggiunge/rimuove skill delta |
| Suggerimenti | `/admin/suggestions` | Suggerimenti AI basati sui feedback, applica/ignora |
| Statistiche | `/admin/stats` | Tasso di approvazione per categoria di ruolo |

### Aggiungere una skill

1. Aprire `/admin/profile`
2. Sezione "Add skill" → digitare la skill → **Add**
3. La skill è attiva al prossimo run (senza riavvio)

### Applicare un suggerimento AI

Dopo qualche settimana di utilizzo, il `PreferenceLearner` (job settimanale) analizza i feedback e suggerisce modifiche al profilo. Aprire `/admin/suggestions` → **Apply** per confermare.

---

## 7. Fonti opzionali

### Backstage (con account attore)

Nel `.env`:
```env
BACKSTAGE_EMAIL=tuo@email.com
BACKSTAGE_PASSWORD=password
BACKSTAGE_ENABLED=true
BACKSTAGE_MAX_LISTINGS=50
```

> **Attenzione:** L'automazione viola i ToS di Backstage. Usare con crawl delay (già configurato: 3s tra pagine) e non più di 50 listing per run.

### Gmail (newsletter casting)

1. Abilitare [App Password](https://myaccount.google.com/apppasswords) sull'account Google
2. Nel `.env`:

```env
GMAIL_ADDRESS=tuo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
GMAIL_CASTING_SENDERS=newsletter@backstage.com,info@castingnetworks.com
GMAIL_ENABLED=true
```

---

## 8. Configurazione avanzata

### Frequenza di monitoraggio

```env
SEARCH_INTERVAL_MINUTES=240   # ogni 4 ore
```

Valori consigliati:
- `120` — ogni 2 ore (uso intensivo, ~€10/mese OpenAI)
- `360` — ogni 6 ore (default, ~€3/mese OpenAI)
- `720` — ogni 12 ore (conservativo, ~€1.50/mese OpenAI)

### Score minimo per notifica

```env
MINIMUM_MATCH_SCORE=0.5   # default 0.3
```

Aumentare se si ricevono troppi listing irrilevanti.

### Numero listing per notifica

```env
NOTIFICATION_TOP_N=3   # default 5
```

---

## 9. Sviluppo locale (senza Docker)

Richiede Python 3.12+, PostgreSQL e Redis in esecuzione.

```bash
pip install -e .[dev]
playwright install chromium   # solo se si usa Backstage
alembic upgrade head
uvicorn app.main:app --reload
```

Test:
```bash
pytest
ruff check app/
mypy app/
```

---

## 10. Troubleshooting

| Problema | Causa probabile | Soluzione |
|---|---|---|
| Bot Telegram silenzioso | Token/chat ID errato o `TELEGRAM_ENABLED=false` | Verificare `.env` |
| Nessun listing trovato | Score troppo alto o profilo non compilato | Abbassare `MINIMUM_MATCH_SIZE` o compilare `actor_profile.yaml` |
| Errore migrazione | DB non raggiungibile | Verificare che il container postgres sia `healthy` prima di eseguire migrate |
| `actor_profile.yaml` non trovato | Path errato | Verificare `ACTOR_PROFILE_PATH` in `.env` (default: `./actor_profile.yaml`) |
| Backstage login failed | Credenziali errate o 2FA attivo | Disabilitare 2FA o usare sessione cookie manuale |
| Gmail: no emails | Sender non in whitelist o email già lette | Verificare `GMAIL_CASTING_SENDERS` e che le email siano UNSEEN |

---

## 11. Costi mensili stimati

| Scenario | OpenAI | Tavily | Infra | Totale |
|---|---|---|---|---|
| Conservativo (ogni 12h, VPS) | ~€0.40 | Free | ~€5 | **~€5.50/mese** |
| Default (ogni 6h, VPS) | ~€0.75 | €9 | ~€5 | **~€15/mese** |
| Intensivo (ogni 2h, VPS) | ~€3 | €9 | ~€5 | **~€17/mese** |

Per dettagli e strategie di riduzione costi: `docs/business-plan-cost-analysis.md`
