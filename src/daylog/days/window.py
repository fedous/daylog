from dataclasses import dataclass
from datetime import date, timedelta


class OutsideEditWindow(Exception):
    """Il giorno è fuori dalla finestra di modifica: troppo indietro o nel futuro."""


@dataclass(frozen=True)
class EditWindow:
    """I giorni in cui si possono cambiare spunte e note: da oggi fino a `days` giorni fa.

    "Oggi" arriva da fuori (la route lo calcola nel fuso Europe/Rome), così si prova senza orologio.
    """

    today: date
    days: int

    def contains(self, day: date) -> bool:
        return self.today - timedelta(days=self.days) <= day <= self.today

    def ensure_contains(self, day: date) -> None:
        if not self.contains(day):
            raise OutsideEditWindow(day)
