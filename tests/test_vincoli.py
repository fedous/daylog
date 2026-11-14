"""I vincoli dell'ADR-0008 che fa rispettare Postgres, qualunque sia il codice che scrive."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from daylog.models import Check, Habit, User


@pytest.fixture
def io(sessione) -> User:
    utente = User(email="io@example.com")
    sessione.add(utente)
    sessione.flush()
    return utente


@pytest.fixture
def lettura(sessione, io) -> Habit:
    abitudine = Habit(user_id=io.id, name="Leggere", kind="quantity", unit="minuti", position=1)
    sessione.add(abitudine)
    sessione.flush()
    return abitudine


def test_due_abitudini_attive_non_possono_avere_lo_stesso_nome(sessione, io):
    sessione.add(Habit(user_id=io.id, name="Meditare", kind="boolean", position=1))
    sessione.flush()

    sessione.add(Habit(user_id=io.id, name="Meditare", kind="boolean", position=2))
    with pytest.raises(IntegrityError):
        sessione.flush()


def test_si_puo_riusare_il_nome_di_un_abitudine_archiviata(sessione, io):
    archiviata = Habit(
        user_id=io.id,
        name="Meditare",
        kind="boolean",
        position=1,
        archived_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    sessione.add(archiviata)
    sessione.flush()

    sessione.add(Habit(user_id=io.id, name="Meditare", kind="boolean", position=2))
    sessione.flush()


def test_un_abitudine_si_no_non_ha_un_unita(sessione, io):
    sessione.add(Habit(user_id=io.id, name="Meditare", kind="boolean", unit="minuti", position=1))
    with pytest.raises(IntegrityError):
        sessione.flush()


def test_il_tipo_di_un_abitudine_e_si_no_o_con_valore(sessione, io):
    sessione.add(Habit(user_id=io.id, name="Meditare", kind="scala", position=1))
    with pytest.raises(IntegrityError):
        sessione.flush()


def test_il_valore_di_una_spunta_e_positivo(sessione, lettura):
    sessione.add(Check(habit_id=lettura.id, day=date(2026, 11, 14), value=0))
    with pytest.raises(IntegrityError):
        sessione.flush()


def test_un_abitudine_ha_al_massimo_una_spunta_al_giorno(sessione, lettura):
    sessione.add(Check(habit_id=lettura.id, day=date(2026, 11, 14), value=20))
    sessione.commit()

    sessione.add(Check(habit_id=lettura.id, day=date(2026, 11, 14), value=15))
    with pytest.raises(IntegrityError):
        sessione.flush()
