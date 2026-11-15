from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from daylog import users
from daylog.config import Settings

CARTELLA = Path(__file__).parent


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
templates = Jinja2Templates(directory=CARTELLA / "templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html")
