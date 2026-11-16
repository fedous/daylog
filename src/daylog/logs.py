"""Log in JSON su stdout, una riga per evento (ADR-0004).

Chi fa girare l'app (la piattaforma, docker) raccoglie stdout: ogni riga è un oggetto JSON
con campi che si possono filtrare, es. `jq 'select(.status >= 500)'`.
"""

import json
import logging
import sys
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TextIO

from fastapi import Request, Response
from fastapi.responses import HTMLResponse

# Gli attributi che logging mette in ogni record: quelli che restano sono i campi di extra=...
_ATTRIBUTI_STANDARD = set(vars(logging.makeLogRecord({}))) | {"message"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        riga = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for nome, valore in vars(record).items():
            if nome not in _ATTRIBUTI_STANDARD:
                riga[nome] = valore
        if record.exc_info:
            # Lo stack ha più righe: json.dumps scrive gli a capo come \n, l'evento resta una riga
            riga["exception"] = self.formatException(record.exc_info)
        return json.dumps(riga)


def configure(stream: TextIO | None = None) -> None:
    """Manda i log di tutto il processo, dal livello INFO in su, su stream (di default stdout).

    Sostituisce gli handler del logger radice invece di aggiungerne: chiamarla due volte non
    raddoppia le righe.
    """
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(JsonFormatter())
    radice = logging.getLogger()
    radice.handlers = [handler]
    radice.setLevel(logging.INFO)
    # Uvicorn ha handler suoi, in testo: i suoi messaggi passano al logger radice e escono in JSON.
    # Il suo log di accesso si spegne: lo sostituisce access_log, con più campi
    for nome in ("uvicorn", "uvicorn.error"):
        logging.getLogger(nome).handlers = []
        logging.getLogger(nome).propagate = True
    logging.getLogger("uvicorn.access").disabled = True


_accessi = logging.getLogger("daylog.access")
_errori = logging.getLogger("daylog.errors")


async def access_log(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Middleware: una riga per ogni richiesta, con metodo, path, status e durata."""
    # perf_counter: un orologio fatto per misurare intervalli, che non salta se cambia l'ora
    inizio = time.perf_counter()
    # url.path senza query string: niente parametri nei log
    path = request.url.path
    try:
        response = await call_next(request)
    except Exception:
        # Arriva qui solo quello che nessun exception handler ha gestito: un bug.
        # Rispondiamo noi, così l'eccezione non sale fino a uvicorn (che la stamperebbe in testo)
        _errori.exception("errore non gestito", extra={"method": request.method, "path": path})
        response = HTMLResponse("Errore del server", status_code=500)
    durata_ms = round((time.perf_counter() - inizio) * 1000, 1)
    _accessi.info(
        "%s %s %d",
        request.method,
        path,
        response.status_code,
        extra={
            "method": request.method,
            "path": path,
            "status": response.status_code,
            "duration_ms": durata_ms,
            # Lo segna get_user_id; le richieste che non ci passano (es. i file statici) non l'hanno
            "user_id": getattr(request.state, "user_id", None),
        },
    )
    return response
