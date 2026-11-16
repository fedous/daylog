from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from daylog import habits, users
from daylog.config import Settings
from daylog.habits import routes as habits_routes
from daylog.web import CARTELLA, templates


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Gira una volta all'avvio (prima di yield) e una allo spegnimento (dopo)."""
    settings = Settings()
    engine = create_engine(settings.database_url)
    with Session(engine) as session, session.begin():
        # L'id va letto qui: dopo il commit gli attributi dell'oggetto scadono
        user_id = users.get_or_create(session, settings.user_email).id
    app.state.engine = engine
    app.state.user_id = user_id
    app.state.edit_window_days = settings.edit_window_days
    yield
    engine.dispose()


app = FastAPI(title="daylog", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=CARTELLA / "static"), name="static")
app.include_router(habits_routes.router)


@app.exception_handler(habits.HabitNotFound)
def habit_not_found(request: Request, exc: habits.HabitNotFound) -> HTMLResponse:
    """Vale per tutte le route: un'abitudine che non c'è, o di un altro utente, è un 404.

    L'eccezione è già uscita dalla route, quindi get_session ha fatto rollback.
    """
    return HTMLResponse("Abitudine non trovata", status_code=404)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html")
