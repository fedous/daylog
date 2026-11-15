from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from daylog import habits
from daylog.days.window import EditWindow
from daylog.db.models import Check, DayNote, Habit


class ValueRequired(Exception):
    """Un'abitudine con valore si spunta solo con un valore positivo."""


class ValueNotAllowed(Exception):
    """Un'abitudine sì/no si spunta senza valore."""


@dataclass(frozen=True)
class HabitDay:
    """Un'abitudine in un giorno: se è fatta e con che valore."""

    habit: Habit
    done: bool
    value: int | None


@dataclass(frozen=True)
class Day:
    """Un giorno: le abitudini attive, in ordine, ciascuna con la sua spunta, e la nota."""

    day: date
    habits: list[HabitDay]
    note: str | None


def _active_habit(session: Session, user_id: int, habit_id: int) -> Habit:
    """L'abitudine dell'utente, se è attiva: un'abitudine archiviata non compare in "oggi"."""
    habit = habits.get_habit(session, user_id, habit_id)
    if habit.archived_at is not None:
        raise habits.HabitNotFound(habit_id)
    return habit


def set_check(
    session: Session,
    user_id: int,
    window: EditWindow,
    habit_id: int,
    day: date,
    value: int | None = None,
) -> None:
    """Spunta un'abitudine in un giorno. Se è già spuntata, ne sovrascrive il valore."""
    window.ensure_contains(day)
    habit = _active_habit(session, user_id, habit_id)
    if habit.kind == "quantity" and (value is None or value <= 0):
        raise ValueRequired(habit.name)
    if habit.kind == "boolean" and value is not None:
        raise ValueNotAllowed(habit.name)
    # Upsert: INSERT ... ON CONFLICT (habit_id, day) DO UPDATE, un solo comando atomico.
    # È un'istruzione Core, non passa dall'ORM: updated_at va aggiornato qui.
    upsert = insert(Check).values(habit_id=habit.id, day=day, value=value)
    upsert = upsert.on_conflict_do_update(
        index_elements=[Check.habit_id, Check.day],
        set_={"value": upsert.excluded.value, "updated_at": func.now()},
    )
    session.execute(upsert)


def remove_check(
    session: Session, user_id: int, window: EditWindow, habit_id: int, day: date
) -> None:
    """Toglie la spunta: la riga si cancella, e il giorno risulta non fatto."""
    window.ensure_contains(day)
    habit = _active_habit(session, user_id, habit_id)
    session.execute(delete(Check).where(Check.habit_id == habit.id, Check.day == day))


def set_note(session: Session, user_id: int, window: EditWindow, day: date, text: str) -> None:
    """Scrive la nota del giorno. Se c'è già, la sovrascrive; una nota vuota la cancella."""
    window.ensure_contains(day)
    if not text.strip():
        session.execute(delete(DayNote).where(DayNote.user_id == user_id, DayNote.day == day))
        return
    upsert = insert(DayNote).values(user_id=user_id, day=day, text=text)
    upsert = upsert.on_conflict_do_update(
        index_elements=[DayNote.user_id, DayNote.day],
        set_={"text": upsert.excluded.text, "updated_at": func.now()},
    )
    session.execute(upsert)


def get_day(session: Session, user_id: int, day: date) -> Day:
    """Il giorno con le abitudini attive. Si legge sempre, anche fuori dalla finestra."""
    active = habits.list_habits(session, user_id)
    query = select(Check.habit_id, Check.value).where(
        Check.day == day, Check.habit_id.in_([h.id for h in active])
    )
    values = dict(session.execute(query).all())
    rows = [
        HabitDay(habit=habit, done=habit.id in values, value=values.get(habit.id))
        for habit in active
    ]
    note = session.scalar(
        select(DayNote.text).where(DayNote.user_id == user_id, DayNote.day == day)
    )
    return Day(day=day, habits=rows, note=note)
