"""La pagina del giorno: le spunte delle abitudini e la nota."""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from daylog import days
from daylog.deps import EditWindowDep, SessionDep, UserIdDep
from daylog.web import templates

router = APIRouter()


def next_day_url(day: date, today: date) -> str | None:
    """Il link al giorno dopo: nessuno da oggi, la pagina di oggi da ieri."""
    if day >= today:
        return None
    following = day + timedelta(days=1)
    return "/" if following == today else f"/days/{following.isoformat()}"


def render_day(
    request: Request, session: Session, user_id: int, day: date, window: days.EditWindow
) -> HTMLResponse:
    today = window.today
    context = {
        "day": days.get_day(session, user_id, day),
        "today": today,
        "editable": window.contains(day),
        "previous": day - timedelta(days=1),
        "next_url": next_day_url(day, today),
    }
    return templates.TemplateResponse(request, "day.html", context)


@router.get("/", response_class=HTMLResponse)
def today_page(request: Request, session: SessionDep, user_id: UserIdDep, window: EditWindowDep):
    return render_day(request, session, user_id, window.today, window)


@router.get("/days/{day}", response_class=HTMLResponse)
def day_page(
    request: Request, session: SessionDep, user_id: UserIdDep, window: EditWindowDep, day: date
):
    if day > window.today:
        raise HTTPException(status_code=404, detail="Il giorno non è ancora arrivato")
    return render_day(request, session, user_id, day, window)


def render_row(
    request: Request,
    session: Session,
    user_id: int,
    day: date,
    habit_id: int,
    error: str | None = None,
) -> HTMLResponse:
    """Il frammento con la riga di un'abitudine; con un errore, lo stato è 422."""
    day_data = days.get_day(session, user_id, day)
    [row] = [row for row in day_data.habits if row.habit.id == habit_id]
    context = {"day": day_data, "row": row, "error": error}
    status_code = 422 if error else 200
    return templates.TemplateResponse(request, "_habit_row.html", context, status_code=status_code)


@router.put("/days/{day}/checks/{habit_id}", response_class=HTMLResponse)
def put_check(
    request: Request,
    session: SessionDep,
    user_id: UserIdDep,
    window: EditWindowDep,
    day: date,
    habit_id: int,
    value: Annotated[int | None, Form()] = None,
):
    try:
        days.set_check(session, user_id, window, habit_id, day, value)
    except days.ValueRequired:
        error = "Scrivi un numero maggiore di zero, o togli la spunta."
        return render_row(request, session, user_id, day, habit_id, error)
    except days.ValueNotAllowed:
        error = "Questa abitudine si spunta senza valore."
        return render_row(request, session, user_id, day, habit_id, error)
    return render_row(request, session, user_id, day, habit_id)


@router.delete("/days/{day}/checks/{habit_id}", response_class=HTMLResponse)
def delete_check(
    request: Request,
    session: SessionDep,
    user_id: UserIdDep,
    window: EditWindowDep,
    day: date,
    habit_id: int,
):
    days.remove_check(session, user_id, window, habit_id, day)
    return render_row(request, session, user_id, day, habit_id)


@router.put("/days/{day}/note", response_class=HTMLResponse)
def put_note(
    request: Request,
    session: SessionDep,
    user_id: UserIdDep,
    window: EditWindowDep,
    day: date,
    # Una textarea vuota arriva come "non mandata": il default "" cancella la nota
    text: Annotated[str, Form()] = "",
):
    days.set_note(session, user_id, window, day, text)
    context = {"day": days.get_day(session, user_id, day), "saved": True}
    return templates.TemplateResponse(request, "_note.html", context)
