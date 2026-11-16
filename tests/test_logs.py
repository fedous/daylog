"""I log in JSON: una riga per evento, con campi che un programma sa leggere (ADR-0004)."""

import io
import json
import logging
from datetime import datetime

import pytest

from daylog import logs
from daylog.deps import get_edit_window
from daylog.main import app


@pytest.fixture
def stream():
    """Uno stdout finto in memoria. Il logger radice è globale: a fine test torna com'era."""
    radice = logging.getLogger()
    handlers, livello = radice.handlers[:], radice.level
    yield io.StringIO()
    radice.handlers = handlers
    radice.setLevel(livello)


def righe_json(stream: io.StringIO) -> list[dict]:
    return [json.loads(riga) for riga in stream.getvalue().splitlines()]


def test_un_log_esce_come_una_riga_json_con_i_campi_extra(stream):
    logs.configure(stream)

    logging.getLogger("daylog.prova").info("spunta salvata", extra={"habit_id": 3})

    [riga] = righe_json(stream)
    assert riga["level"] == "INFO"
    assert riga["logger"] == "daylog.prova"
    assert riga["message"] == "spunta salvata"
    assert riga["habit_id"] == 3
    # Data e ora in ISO 8601 con il fuso: si confrontano log di macchine diverse
    assert datetime.fromisoformat(riga["time"]).tzinfo is not None


def test_un_errore_porta_lo_stack_in_un_campo_e_resta_una_riga(stream):
    logs.configure(stream)

    try:
        raise ValueError("valore sbagliato")
    except ValueError:
        # exception(): livello ERROR, più l'eccezione che si sta gestendo
        logging.getLogger("daylog.prova").exception("calcolo fallito")

    [riga] = righe_json(stream)
    assert riga["level"] == "ERROR"
    assert riga["message"] == "calcolo fallito"
    assert riga["exception"].startswith("Traceback")
    assert "ValueError: valore sbagliato" in riga["exception"]


def accessi(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """I log di accesso catturati da caplog (la fixture di pytest che raccoglie i log)."""
    return [record for record in caplog.records if record.name == "daylog.access"]


def test_ogni_richiesta_lascia_un_log_di_accesso(client, caplog):
    # Di default passano solo i WARNING: per vedere gli INFO va abbassato il livello
    caplog.set_level(logging.INFO, logger="daylog.access")

    client.get("/habits")

    [accesso] = accessi(caplog)
    assert accesso.getMessage() == "GET /habits 200"
    assert accesso.method == "GET"
    assert accesso.path == "/habits"
    assert accesso.status == 200
    assert accesso.duration_ms >= 0


@pytest.mark.parametrize(
    ("metodo", "url", "path", "status"),
    [
        # Una pagina che non c'è
        ("GET", "/pagina-che-non-esiste", "/pagina-che-non-esiste", 404),
        # Manca il campo direction del form: FastAPI risponde 422 prima di entrare nella route
        ("POST", "/habits/1/move", "/habits/1/move", 422),
        # La query string resta fuori dal log
        ("GET", "/history?da=ieri", "/history", 200),
    ],
)
def test_il_log_di_accesso_ha_lo_status_vero_e_il_path_senza_query(
    client, caplog, metodo, url, path, status
):
    caplog.set_level(logging.INFO, logger="daylog.access")

    client.request(metodo, url)

    [accesso] = accessi(caplog)
    assert accesso.path == path
    assert accesso.status == status


def test_un_errore_inatteso_lascia_lo_stack_e_un_accesso_con_500(client, caplog):
    caplog.set_level(logging.INFO, logger="daylog")

    def guasto():
        raise RuntimeError("database sparito")

    # La fixture client cancella gli override a fine test
    app.dependency_overrides[get_edit_window] = guasto

    risposta = client.get("/")

    assert risposta.status_code == 500
    [errore] = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert errore.name == "daylog.errors"
    assert errore.path == "/"
    # exc_info: l'eccezione allegata al log, da cui il formatter ricava lo stack
    assert isinstance(errore.exc_info[1], RuntimeError)
    [accesso] = accessi(caplog)
    assert accesso.status == 500


@pytest.mark.parametrize(
    ("url", "con_utente"),
    [
        ("/habits", True),
        # I file statici non passano da get_user_id: nessun utente
        ("/static/style.css", False),
    ],
)
def test_il_log_di_accesso_dice_quale_utente_ha_fatto_la_richiesta(
    client, caplog, io, url, con_utente
):
    caplog.set_level(logging.INFO, logger="daylog.access")

    client.get(url)

    [accesso] = accessi(caplog)
    assert accesso.user_id == (io.id if con_utente else None)
