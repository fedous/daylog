# daylog

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

## Configurazione

Variabili d'ambiente, anche da un file `.env` (non va nella repo). I default sono quelli dello sviluppo in locale.

| Variabile | Default | Cosa fa |
|---|---|---|
| `DATABASE_URL` | il Postgres di `compose.yaml` | connessione al database |
| `DAYLOG_USER_EMAIL` | `io@example.com` | l'utente unico, cercato o creato all'avvio |
| `DAYLOG_EDIT_WINDOW_DAYS` | `7` | fino a quanti giorni fa si cambiano spunte e note |

## Licenza

MIT, vedi [LICENSE](LICENSE).
