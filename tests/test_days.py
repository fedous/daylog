"""I giorni: spunte, nota del giorno e finestra di modifica."""

from datetime import date, timedelta

import pytest

from daylog import days, habits

OGGI = date(2026, 11, 15)
IERI = OGGI - timedelta(days=1)
FINESTRA = days.EditWindow(today=OGGI, days=7)


@pytest.mark.parametrize("giorni_fa", [0, 1, 7], ids=["oggi", "ieri", "7 giorni fa"])
def test_la_finestra_va_da_oggi_a_7_giorni_fa(giorni_fa):
    finestra = days.EditWindow(today=OGGI, days=7)

    assert finestra.contains(OGGI - timedelta(days=giorni_fa))


@pytest.mark.parametrize("giorni_fa", [8, -1], ids=["8 giorni fa", "domani"])
def test_fuori_dalla_finestra_ci_sono_il_passato_lontano_e_il_futuro(giorni_fa):
    finestra = days.EditWindow(today=OGGI, days=7)

    assert not finestra.contains(OGGI - timedelta(days=giorni_fa))


def fatte(giorno: days.Day) -> dict[str, bool]:
    """Le abitudini del giorno, con il nome e se sono fatte."""
    return {riga.habit.name: riga.done for riga in giorno.habits}


def test_un_abitudine_spuntata_risulta_fatta_in_quel_giorno_e_non_negli_altri(sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")

    days.set_check(sessione, io.id, FINESTRA, meditare.id, OGGI)

    assert fatte(days.get_day(sessione, io.id, OGGI)) == {"Meditare": True}
    assert fatte(days.get_day(sessione, io.id, IERI)) == {"Meditare": False}


def valori(giorno: days.Day) -> dict[str, int | None]:
    """Le abitudini del giorno, con il nome e il valore della spunta."""
    return {riga.habit.name: riga.value for riga in giorno.habits}


def test_un_abitudine_con_valore_mostra_il_valore_della_spunta(sessione, io):
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    days.set_check(sessione, io.id, FINESTRA, lettura.id, OGGI, value=20)

    assert valori(days.get_day(sessione, io.id, OGGI)) == {"Leggere": 20}


def test_spuntare_di_nuovo_sovrascrive_il_valore(sessione, io):
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    days.set_check(sessione, io.id, FINESTRA, lettura.id, OGGI, value=20)

    days.set_check(sessione, io.id, FINESTRA, lettura.id, OGGI, value=35)

    assert valori(days.get_day(sessione, io.id, OGGI)) == {"Leggere": 35}


@pytest.mark.parametrize("valore", [None, 0, -5], ids=["senza valore", "zero", "negativo"])
def test_un_abitudine_con_valore_si_spunta_solo_con_un_valore_positivo(sessione, io, valore):
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    with pytest.raises(days.ValueRequired):
        days.set_check(sessione, io.id, FINESTRA, lettura.id, OGGI, value=valore)


def test_un_abitudine_si_no_non_accetta_un_valore(sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")

    with pytest.raises(days.ValueNotAllowed):
        days.set_check(sessione, io.id, FINESTRA, meditare.id, OGGI, value=10)


def test_togliere_la_spunta_rende_il_giorno_non_fatto(sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    days.set_check(sessione, io.id, FINESTRA, meditare.id, OGGI)

    days.remove_check(sessione, io.id, FINESTRA, meditare.id, OGGI)

    assert fatte(days.get_day(sessione, io.id, OGGI)) == {"Meditare": False}


def test_togliere_una_spunta_che_non_c_e_non_da_errore(sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")

    days.remove_check(sessione, io.id, FINESTRA, meditare.id, OGGI)

    assert fatte(days.get_day(sessione, io.id, OGGI)) == {"Meditare": False}


def test_la_nota_del_giorno_si_salva(sessione, io):
    days.set_note(sessione, io.id, FINESTRA, OGGI, "Giornata lunga, ma ho letto.")

    assert days.get_day(sessione, io.id, OGGI).note == "Giornata lunga, ma ho letto."
    assert days.get_day(sessione, io.id, IERI).note is None


def test_scrivere_di_nuovo_la_nota_la_sovrascrive(sessione, io):
    days.set_note(sessione, io.id, FINESTRA, OGGI, "Prima versione")

    days.set_note(sessione, io.id, FINESTRA, OGGI, "Seconda versione")

    assert days.get_day(sessione, io.id, OGGI).note == "Seconda versione"


@pytest.mark.parametrize("vuota", ["", "  \n "], ids=["vuota", "solo spazi"])
def test_una_nota_vuota_cancella_quella_che_c_era(sessione, io, vuota):
    days.set_note(sessione, io.id, FINESTRA, OGGI, "Da cancellare")

    days.set_note(sessione, io.id, FINESTRA, OGGI, vuota)

    assert days.get_day(sessione, io.id, OGGI).note is None


MODIFICHE = {
    "spuntare": lambda s, user_id, habit_id, giorno: days.set_check(
        s, user_id, FINESTRA, habit_id, giorno
    ),
    "togliere la spunta": lambda s, user_id, habit_id, giorno: days.remove_check(
        s, user_id, FINESTRA, habit_id, giorno
    ),
    "scrivere la nota": lambda s, user_id, habit_id, giorno: days.set_note(
        s, user_id, FINESTRA, giorno, "Troppo tardi"
    ),
}


@pytest.mark.parametrize("modifica", MODIFICHE.values(), ids=MODIFICHE.keys())
def test_fuori_dalla_finestra_il_giorno_non_si_modifica(sessione, io, modifica):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")

    with pytest.raises(days.OutsideEditWindow):
        modifica(sessione, io.id, meditare.id, OGGI - timedelta(days=8))


def di_un_altro_utente(sessione, io, altro) -> int:
    return habits.create_habit(sessione, altro.id, "Correre", "boolean").id


def archiviata(sessione, io, altro) -> int:
    abitudine = habits.create_habit(sessione, io.id, "Correre", "boolean")
    habits.archive(sessione, io.id, abitudine.id)
    return abitudine.id


SPUNTE = {
    "spuntare": lambda s, user_id, habit_id: days.set_check(s, user_id, FINESTRA, habit_id, OGGI),
    "togliere la spunta": lambda s, user_id, habit_id: days.remove_check(
        s, user_id, FINESTRA, habit_id, OGGI
    ),
}


@pytest.mark.parametrize("abitudine", [di_un_altro_utente, archiviata], ids=lambda f: f.__name__)
@pytest.mark.parametrize("spunta", SPUNTE.values(), ids=SPUNTE.keys())
def test_si_spuntano_solo_le_proprie_abitudini_attive(sessione, io, altro, abitudine, spunta):
    habit_id = abitudine(sessione, io, altro)

    with pytest.raises(habits.HabitNotFound):
        spunta(sessione, io.id, habit_id)


def test_il_giorno_mostra_le_abitudini_attive_in_ordine_ciascuna_con_la_sua_spunta(
    sessione, io, altro
):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    corsa = habits.create_habit(sessione, io.id, "Correre", "boolean")
    habits.create_habit(sessione, io.id, "Scrivere", "boolean")
    nuoto = habits.create_habit(sessione, altro.id, "Nuotare", "boolean")
    days.set_check(sessione, io.id, FINESTRA, meditare.id, OGGI)
    days.set_check(sessione, io.id, FINESTRA, meditare.id, IERI)
    days.set_check(sessione, io.id, FINESTRA, lettura.id, OGGI, value=20)
    days.set_check(sessione, io.id, FINESTRA, corsa.id, OGGI)
    habits.archive(sessione, io.id, corsa.id)
    days.set_check(sessione, altro.id, FINESTRA, nuoto.id, OGGI)

    righe = days.get_day(sessione, io.id, OGGI).habits

    assert [(riga.habit.name, riga.done, riga.value) for riga in righe] == [
        ("Meditare", True, None),
        ("Leggere", True, 20),
        ("Scrivere", False, None),
    ]
