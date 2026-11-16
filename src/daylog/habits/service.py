from collections.abc import Generator
from contextlib import contextmanager
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from daylog.db.models import Habit

UNIQUE_ACTIVE_NAME = "uq_habits_user_id_name_active"

# "up" verso la cima della lista, "down" verso il fondo
type Direction = Literal["up", "down"]


class DuplicateHabitName(Exception):
    """C'è già un'abitudine attiva con questo nome."""


class EmptyHabitName(Exception):
    """Il nome è vuoto, o fatto solo di spazi."""


class HabitNotFound(Exception):
    """L'abitudine non esiste, o è di un altro utente."""


def get_habit(session: Session, user_id: int, habit_id: int) -> Habit:
    """L'abitudine, se esiste ed è dell'utente."""
    query = select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    habit = session.scalar(query)
    if habit is None:
        raise HabitNotFound(habit_id)
    return habit


@contextmanager
def _unique_name(session: Session, name: str) -> Generator[None]:
    """Salva le modifiche fatte nel blocco e traduce la violazione del nome unico.

    SAVEPOINT: se il salvataggio fallisce, la transazione della richiesta resta usabile.
    begin_nested() fa un flush prima di aprirlo, quindi le modifiche vanno fatte dentro il blocco.
    """
    try:
        with session.begin_nested():
            yield
    except IntegrityError as e:
        if e.orig.diag.constraint_name == UNIQUE_ACTIVE_NAME:
            raise DuplicateHabitName(name) from e
        raise


def _clean_name(name: str) -> str:
    """Il nome senza spazi ai lati, che non può restare vuoto."""
    name = name.strip()
    if not name:
        raise EmptyHabitName()
    return name


def _next_position(session: Session, user_id: int) -> int:
    """La posizione in fondo alla lista."""
    last = session.scalar(
        select(func.coalesce(func.max(Habit.position), 0)).where(Habit.user_id == user_id)
    )
    return last + 1


def create_habit(
    session: Session, user_id: int, name: str, kind: str, unit: str | None = None
) -> Habit:
    """Crea un'abitudine in fondo alla lista."""
    name = _clean_name(name)
    position = _next_position(session, user_id)
    habit = Habit(user_id=user_id, name=name, kind=kind, unit=unit, position=position)
    with _unique_name(session, name):
        session.add(habit)
    return habit


def update_habit(
    session: Session, user_id: int, habit_id: int, *, name: str, unit: str | None
) -> Habit:
    """Cambia nome e unità. Il tipo non si cambia: si archivia e se ne crea un'altra."""
    name = _clean_name(name)
    habit = get_habit(session, user_id, habit_id)
    with _unique_name(session, name):
        habit.name = name
        habit.unit = unit
    return habit


def archive(session: Session, user_id: int, habit_id: int) -> None:
    """Toglie l'abitudine da "oggi". Le spunte restano, e il nome si può riusare."""
    habit = get_habit(session, user_id, habit_id)
    habit.archived_at = func.now()
    session.flush()


def restore(session: Session, user_id: int, habit_id: int) -> Habit:
    """Riporta un'abitudine archiviata tra le attive, in fondo alla lista."""
    habit = get_habit(session, user_id, habit_id)
    # Prima della query: la SELECT farebbe un autoflush delle modifiche fuori dal SAVEPOINT
    position = _next_position(session, user_id)
    with _unique_name(session, habit.name):
        habit.archived_at = None
        habit.position = position
    return habit


def move(session: Session, user_id: int, habit_id: int, direction: Direction) -> None:
    """Sposta l'abitudine di un posto, scambiandola con la vicina."""
    habit = get_habit(session, user_id, habit_id)
    # La vicina è l'attiva più vicina sopra (posizione minore) o sotto (maggiore)
    if direction == "up":
        side, nearest_first = Habit.position < habit.position, Habit.position.desc()
    else:
        side, nearest_first = Habit.position > habit.position, Habit.position.asc()
    query = (
        select(Habit)
        .where(Habit.user_id == user_id, Habit.archived_at.is_(None), side)
        .order_by(nearest_first)
        .limit(1)
    )
    neighbor = session.scalar(query)
    if neighbor is None:  # è già in cima, o già in fondo
        return
    habit.position, neighbor.position = neighbor.position, habit.position


def list_habits(session: Session, user_id: int, *, archived: bool = False) -> list[Habit]:
    """Le abitudini attive (o quelle archiviate), nell'ordine in cui compaiono."""
    state = Habit.archived_at.is_not(None) if archived else Habit.archived_at.is_(None)
    query = select(Habit).where(Habit.user_id == user_id, state).order_by(Habit.position)
    return list(session.scalars(query))
