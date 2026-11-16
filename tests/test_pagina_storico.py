"""La pagina dello storico, provata via HTTP: serie in corso e record di ogni abitudine.

Il calcolo delle serie è già provato in test_history.py: qui si controlla che arrivi nella pagina.
"""

from datetime import timedelta

import pytest

from daylog import days, habits
from daylog.days import EditWindow


@pytest.fixture
def passato(oggi) -> EditWindow:
    """Una finestra larga, solo per preparare spunte più vecchie di 7 giorni."""
    return EditWindow(today=oggi, days=60)


def spunta(sessione, io, finestra, habit_id, *giorni):
    for giorno in giorni:
        days.set_check(sessione, io.id, finestra, habit_id, giorno)


def test_lo_storico_mostra_la_serie_in_corso_e_il_record(client, sessione, io, oggi, passato):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    # Oggi e ieri: serie in corso di 2. Da 14 a 10 giorni fa: record di 5.
    spunta(sessione, io, passato, meditare.id, oggi, oggi - timedelta(days=1))
    spunta(sessione, io, passato, meditare.id, *(oggi - timedelta(days=n) for n in range(10, 15)))

    risposta = client.get("/history")

    assert risposta.status_code == 200
    assert "serie in corso 2 giorni" in risposta.text
    assert "record 5 giorni" in risposta.text


def test_lo_storico_segue_l_ordine_delle_abitudini_attive(client, sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    correre = habits.create_habit(sessione, io.id, "Correre", "boolean")
    habits.archive(sessione, io.id, correre.id)

    pagina = client.get("/history").text

    assert pagina.index("Meditare") < pagina.index("Leggere")
    assert "Correre" not in pagina


def test_un_giorno_solo_si_scrive_al_singolare(client, sessione, io, oggi, finestra):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    spunta(sessione, io, finestra, meditare.id, oggi)

    pagina = client.get("/history").text

    assert "serie in corso 1 giorno ·" in pagina
    assert "record 1 giorno" in pagina


def test_senza_abitudini_lo_storico_dice_come_cominciare(client, sessione, io):
    assert "Nessuna abitudine ancora" in client.get("/history").text

    habits.create_habit(sessione, io.id, "Meditare", "boolean")

    assert "Nessuna abitudine ancora" not in client.get("/history").text
