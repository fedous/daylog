# daylog

[![CI](https://github.com/fedous/daylog/actions/workflows/ci.yml/badge.svg)](https://github.com/fedous/daylog/actions/workflows/ci.yml)

Tracker personale per la costanza: abitudini fisse da spuntare ogni giorno (con un valore opzionale, es. minuti) e una nota libera al giorno. Webapp installabile come PWA.

Stack: Python con FastAPI, Jinja2 e HTMX, PostgreSQL. Si gestisce con uv.

> In sviluppo: per ora gira solo in locale.

## Sviluppo

Serve [uv](https://docs.astral.sh/uv/): scarica da solo Python 3.14 e le dipendenze.

```bash
uv run fastapi dev src/daylog/main.py   # server con ricarica automatica su http://localhost:8000
uv run pytest                           # test
uv run ruff check && uv run ruff format # lint e formattazione
```

La CI (`.github/workflows/ci.yml`) rifà gli stessi controlli a ogni push e pull request: `ruff check`, `ruff format --check` e `pytest`, con Postgres in un container come in locale.

### Log

I log escono in JSON su stdout, una riga per evento: una per ogni richiesta (`daylog.access`, con `method`, `path` senza query string, `status`, `duration_ms`, `user_id`) e una con lo stack per ogni errore non gestito (`daylog.errors`). Si leggono con [jq](https://jqlang.org/):

```bash
PYTHONUNBUFFERED=1 uv run fastapi dev src/daylog/main.py | jq -R 'fromjson? // .'
jq 'select(.status >= 500)' log.txt   # solo gli errori del server
```

`PYTHONUNBUFFERED=1` serve quando stdout va in una pipe: senza, Python manda le righe a blocchi.

## Configurazione

Variabili d'ambiente, anche da un file `.env` (non va nella repo). I default sono quelli dello sviluppo in locale.

| Variabile | Default | Cosa fa |
|---|---|---|
| `DATABASE_URL` | il Postgres di `compose.yaml` | connessione al database |
| `DAYLOG_USER_EMAIL` | `io@example.com` | l'utente unico, cercato o creato all'avvio |
| `DAYLOG_EDIT_WINDOW_DAYS` | `7` | fino a quanti giorni fa si cambiano spunte e note |

## Licenza

MIT, vedi [LICENSE](LICENSE).
