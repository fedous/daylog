"""Le pagine del catalogo: elenco, creazione, modifica, archivio e riordino."""

from typing import Annotated, Literal

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from daylog import habits
from daylog.deps import SessionDep, UserIdDep
from daylog.web import templates

router = APIRouter(prefix="/habits")


def back_to_list() -> RedirectResponse:
    """POST-redirect-GET: dopo un form si torna all'elenco, e ricaricare non rimanda il form."""
    return RedirectResponse("/habits", status_code=303)


def render_page(
    request: Request, session: Session, user_id: int, error: str | None = None
) -> HTMLResponse:
    """L'elenco delle abitudini; con un errore, lo stato è 422 e il messaggio sta sopra il form."""
    context = {
        "active": habits.list_habits(session, user_id),
        "archived": habits.list_habits(session, user_id, archived=True),
        "error": error,
    }
    status_code = 422 if error else 200
    return templates.TemplateResponse(request, "habits.html", context, status_code=status_code)


# Gli errori sul nome scritto nel form: la pagina li mostra sopra il form, con lo stato 422
NAME_ERRORS = (habits.DuplicateHabitName, habits.EmptyHabitName)


def name_error(error: Exception) -> str:
    """Il messaggio per l'utente. DuplicateHabitName contiene il nome già senza spazi ai lati."""
    if isinstance(error, habits.EmptyHabitName):
        return "Il nome non può essere vuoto."
    return f"Il nome «{error}» è già usato da un'altra abitudine attiva."


@router.get("", response_class=HTMLResponse)
def habits_page(request: Request, session: SessionDep, user_id: UserIdDep):
    return render_page(request, session, user_id)


@router.post("")
def create(
    request: Request,
    session: SessionDep,
    user_id: UserIdDep,
    name: Annotated[str, Form()],
    kind: Annotated[Literal["boolean", "quantity"], Form()],
    unit: Annotated[str | None, Form()] = None,
):
    try:
        habits.create_habit(session, user_id, name, kind, unit)
    except NAME_ERRORS as e:
        return render_page(request, session, user_id, name_error(e))
    return back_to_list()


@router.post("/{habit_id}")
def update(
    request: Request,
    session: SessionDep,
    user_id: UserIdDep,
    habit_id: int,
    name: Annotated[str, Form()],
    unit: Annotated[str | None, Form()] = None,
):
    try:
        habits.update_habit(session, user_id, habit_id, name=name, unit=unit)
    except NAME_ERRORS as e:
        return render_page(request, session, user_id, name_error(e))
    return back_to_list()


@router.post("/{habit_id}/archive")
def archive(session: SessionDep, user_id: UserIdDep, habit_id: int):
    habits.archive(session, user_id, habit_id)
    return back_to_list()


@router.post("/{habit_id}/restore")
def restore(request: Request, session: SessionDep, user_id: UserIdDep, habit_id: int):
    try:
        habits.restore(session, user_id, habit_id)
    except habits.DuplicateHabitName as e:
        return render_page(request, session, user_id, name_error(e))
    return back_to_list()


@router.post("/{habit_id}/move")
def move(
    session: SessionDep,
    user_id: UserIdDep,
    habit_id: int,
    direction: Annotated[habits.Direction, Form()],
):
    habits.move(session, user_id, habit_id, direction)
    return back_to_list()
