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

## Licenza

MIT, vedi [LICENSE](LICENSE).
