import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from daylog import days, habits, logs, users
from daylog.config import Settings
from daylog.days import routes as days_routes
from daylog.habits import routes as habits_routes
from daylog.history import routes as history_routes
from daylog.web import CARTELLA

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Gira una volta all'avvio (prima di yield) e una allo spegnimento (dopo)."""
    # Per primo: da qui in poi tutti i log, anche quelli di uvicorn, escono in JSON su stdout
    logs.configure()
    settings = Settings()
    engine = create_engine(settings.database_url)
    with Session(engine) as session, session.begin():
        # L'id va letto qui: dopo il commit gli attributi dell'oggetto scadono
        user_id = users.get_or_create(session, settings.user_email).id
    app.state.engine = engine
    app.state.user_id = user_id
    app.state.edit_window_days = settings.edit_window_days
    # L'id e non l'email: nei log niente dati personali
    logger.info(
        "daylog avviato",
        extra={"user_id": user_id, "edit_window_days": settings.edit_window_days},
    )
    yield
    engine.dispose()


app = FastAPI(title="daylog", lifespan=lifespan)
app.middleware("http")(logs.access_log)
app.mount("/static", StaticFiles(directory=CARTELLA / "static"), name="static")
app.include_router(days_routes.router)
app.include_router(habits_routes.router)
app.include_router(history_routes.router)


@app.exception_handler(habits.HabitNotFound)
def habit_not_found(request: Request, exc: habits.HabitNotFound) -> HTMLResponse:
    """Vale per tutte le route: un'abitudine che non c'è, o di un altro utente, è un 404.

    L'eccezione è già uscita dalla route, quindi get_session ha fatto rollback.
    """
    return HTMLResponse("Abitudine non trovata", status_code=404)


@app.exception_handler(days.OutsideEditWindow)
def outside_edit_window(request: Request, exc: days.OutsideEditWindow) -> HTMLResponse:
    """Un giorno troppo indietro (o nel futuro): si legge, ma non si cambia."""
    return HTMLResponse("Questo giorno non si può più modificare", status_code=403)
