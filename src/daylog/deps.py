"""Le dependency delle route: sessione, utente, oggi e finestra di modifica."""

from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from daylog.days import EditWindow
from daylog.db.session import get_session

ROME = ZoneInfo("Europe/Rome")


def get_user_id(request: Request) -> int:
    """L'utente unico della fase 2, trovato o creato dal lifespan.

    Lo segna anche in request.state, che vive quanto la richiesta: il log di accesso lo legge da lì.
    """
    user_id = request.app.state.user_id
    request.state.user_id = user_id
    return user_id


def get_today() -> date:
    """Il giorno in corso nel fuso Europe/Rome, non quello del server (che di solito è in UTC)."""
    return datetime.now(ROME).date()


def get_edit_window(request: Request, today: Annotated[date, Depends(get_today)]) -> EditWindow:
    return EditWindow(today=today, days=request.app.state.edit_window_days)


# scope="function": il commit avviene prima che parta la risposta, non dopo
SessionDep = Annotated[Session, Depends(get_session, scope="function")]
UserIdDep = Annotated[int, Depends(get_user_id)]
TodayDep = Annotated[date, Depends(get_today)]
EditWindowDep = Annotated[EditWindow, Depends(get_edit_window)]
