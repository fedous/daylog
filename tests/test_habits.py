"""Il catalogo delle abitudini, provato dalla sua interfaccia con un Postgres vero."""

import pytest

from daylog import habits
from daylog.db.models import User


def test_un_abitudine_nuova_compare_in_fondo_alla_lista(sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    nomi = [abitudine.name for abitudine in habits.list_habits(sessione, io.id)]

    assert nomi == ["Meditare", "Leggere"]


def test_due_abitudini_attive_non_possono_avere_lo_stesso_nome(sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")

    with pytest.raises(habits.DuplicateHabitName):
        habits.create_habit(sessione, io.id, "Meditare", "boolean")


def test_il_nome_si_salva_senza_spazi_ai_lati(sessione, io):
    habits.create_habit(sessione, io.id, "  Leggere ", "quantity", unit="minuti")

    assert [abitudine.name for abitudine in habits.list_habits(sessione, io.id)] == ["Leggere"]


def test_i_nomi_doppi_si_riconoscono_anche_con_maiuscole_diverse(sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")

    with pytest.raises(habits.DuplicateHabitName):
        habits.create_habit(sessione, io.id, "meditare", "boolean")


def test_un_abitudine_si_puo_rinominare_e_cambiarle_unita(sessione, io):
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    habits.update_habit(sessione, io.id, lettura.id, name="Leggere libri", unit="pagine")

    [abitudine] = habits.list_habits(sessione, io.id)
    assert (abitudine.name, abitudine.unit) == ("Leggere libri", "pagine")


def test_non_si_puo_rinominare_un_abitudine_con_il_nome_di_un_altra_attiva(sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    with pytest.raises(habits.DuplicateHabitName):
        habits.update_habit(sessione, io.id, lettura.id, name=" meditare ", unit="minuti")


def test_dopo_un_nome_doppio_la_sessione_si_puo_ancora_usare(sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    with pytest.raises(habits.DuplicateHabitName):
        habits.update_habit(sessione, io.id, lettura.id, name="Meditare", unit="minuti")

    nomi = [abitudine.name for abitudine in habits.list_habits(sessione, io.id)]

    assert nomi == ["Meditare", "Leggere"]


def test_un_abitudine_archiviata_sparisce_dalle_attive(sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    habits.archive(sessione, io.id, meditare.id)

    assert [abitudine.name for abitudine in habits.list_habits(sessione, io.id)] == ["Leggere"]


def test_un_abitudine_archiviata_compare_tra_le_archiviate(sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    habits.archive(sessione, io.id, meditare.id)

    archiviate = habits.list_habits(sessione, io.id, archived=True)
    assert [abitudine.name for abitudine in archiviate] == ["Meditare"]


def test_un_abitudine_ripristinata_torna_in_fondo_alle_attive(sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    habits.archive(sessione, io.id, meditare.id)

    habits.restore(sessione, io.id, meditare.id)

    nomi = [abitudine.name for abitudine in habits.list_habits(sessione, io.id)]
    assert nomi == ["Leggere", "Meditare"]


def test_non_si_puo_ripristinare_un_abitudine_se_il_nome_e_stato_riusato(sessione, io):
    vecchia = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.archive(sessione, io.id, vecchia.id)
    habits.create_habit(sessione, io.id, "Meditare", "boolean")

    with pytest.raises(habits.DuplicateHabitName):
        habits.restore(sessione, io.id, vecchia.id)


@pytest.fixture
def altro(sessione) -> User:
    """Un secondo utente, per controllare che ognuno veda solo le sue abitudini."""
    utente = User(email="altro@example.com")
    sessione.add(utente)
    sessione.flush()
    return utente


MODIFICHE = {
    "rinominare": lambda s, user_id, habit_id: habits.update_habit(
        s, user_id, habit_id, name="Mia", unit=None
    ),
    "archiviare": habits.archive,
    "ripristinare": habits.restore,
}


@pytest.mark.parametrize("modifica", MODIFICHE.values(), ids=MODIFICHE.keys())
def test_non_si_modifica_un_abitudine_di_un_altro_utente(sessione, io, altro, modifica):
    sua = habits.create_habit(sessione, altro.id, "Correre", "boolean")

    with pytest.raises(habits.HabitNotFound):
        modifica(sessione, io.id, sua.id)


def test_le_abitudini_di_un_altro_utente_non_compaiono(sessione, io, altro):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, altro.id, "Correre", "boolean")

    assert [abitudine.name for abitudine in habits.list_habits(sessione, io.id)] == ["Meditare"]
