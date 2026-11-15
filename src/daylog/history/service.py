from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from daylog import habits
from daylog.db.models import Check, Habit
from daylog.history.streaks import Streaks, streaks


@dataclass(frozen=True)
class HabitHistory:
    """Un'abitudine nello storico, con la serie in corso e il record."""

    habit: Habit
    streaks: Streaks


def get_history(session: Session, user_id: int, today: date) -> list[HabitHistory]:
    """Le abitudini attive, in ordine, ciascuna con le sue serie."""
    active = habits.list_habits(session, user_id)
    query = select(Check.habit_id, Check.day).where(Check.habit_id.in_([h.id for h in active]))
    # Tutte le spunte in una query, poi un insieme di giorni per abitudine
    checked: defaultdict[int, set[date]] = defaultdict(set)
    for habit_id, day in session.execute(query):
        checked[habit_id].add(day)
    return [
        HabitHistory(habit=habit, streaks=streaks(checked[habit.id], today)) for habit in active
    ]
