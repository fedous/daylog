from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Streaks:
    """Le serie di un'abitudine: quella in corso e il record."""

    current: int
    best: int


def _run_ending_on(days: set[date], day: date) -> int:
    """I giorni spuntati di fila che finiscono in `day`, contati all'indietro."""
    count = 0
    while day in days:
        count += 1
        day -= timedelta(days=1)
    return count


def streaks(days: set[date], today: date) -> Streaks:
    """Serie in corso e record, dai giorni con una spunta. "Oggi" arriva da fuori."""
    # Finché oggi non è spuntata la serie non è interrotta: si conta da ieri
    start = today if today in days else today - timedelta(days=1)
    current = _run_ending_on(days, start)
    # Una serie finisce dove il giorno dopo non è spuntato: si conta ognuna una volta sola
    ends = (day for day in days if day + timedelta(days=1) not in days)
    best = max((_run_ending_on(days, end) for end in ends), default=0)
    return Streaks(current=current, best=best)
