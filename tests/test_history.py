"""Lo storico: serie in corso e record di ogni abitudine."""

from datetime import date, timedelta

from daylog import days, habits, history

OGGI = date(2026, 11, 15)
FINESTRA = days.EditWindow(today=OGGI, days=7)


def fa(giorni: int) -> date:
    """Il giorno di `giorni` giorni fa: fa(0) è oggi, fa(1) ieri."""
    return OGGI - timedelta(days=giorni)


def test_senza_spunte_non_ci_sono_serie():
    assert history.streaks(set(), OGGI) == history.Streaks(current=0, best=0)


def test_spuntata_solo_oggi_la_serie_e_di_un_giorno():
    assert history.streaks({OGGI}, OGGI) == history.Streaks(current=1, best=1)


def test_tre_giorni_di_fila_fino_a_oggi_fanno_una_serie_di_tre():
    spunte = {fa(0), fa(1), fa(2)}

    assert history.streaks(spunte, OGGI) == history.Streaks(current=3, best=3)


def test_se_oggi_non_e_ancora_spuntata_la_serie_arriva_fino_a_ieri():
    spunte = {fa(1), fa(2)}

    assert history.streaks(spunte, OGGI) == history.Streaks(current=2, best=2)


def test_un_giorno_saltato_azzera_la_serie_in_corso_ma_non_il_record():
    spunte = {fa(2), fa(3)}

    assert history.streaks(spunte, OGGI) == history.Streaks(current=0, best=2)


def test_il_record_e_la_serie_piu_lunga_anche_se_e_nel_passato():
    in_corso = {fa(0), fa(1)}
    record = {fa(10), fa(11), fa(12), fa(13)}
    breve = {fa(20), fa(21)}

    assert history.streaks(in_corso | record | breve, OGGI) == history.Streaks(current=2, best=4)


def spunta(sessione, utente, abitudine, *giorni_fa: int) -> None:
    """Spunta un'abitudine sì/no nei giorni indicati, contati da oggi."""
    for giorni in giorni_fa:
        days.set_check(sessione, utente.id, FINESTRA, abitudine.id, fa(giorni))


def test_lo_storico_mostra_le_serie_di_un_abitudine_dalle_sue_spunte(sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    spunta(sessione, io, meditare, 1, 2, 4, 5, 6)

    storico = history.get_history(sessione, io.id, OGGI)

    assert [(riga.habit.name, riga.streaks) for riga in storico] == [
        ("Meditare", history.Streaks(current=2, best=3)),
    ]


def test_ogni_abitudine_ha_le_sue_serie_nell_ordine_del_catalogo(sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Camminare", "boolean")
    leggere = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    spunta(sessione, io, meditare, 0, 1, 2)
    days.set_check(sessione, io.id, FINESTRA, leggere.id, fa(0), value=20)

    storico = history.get_history(sessione, io.id, OGGI)

    assert [(riga.habit.name, riga.streaks) for riga in storico] == [
        ("Meditare", history.Streaks(current=3, best=3)),
        ("Camminare", history.Streaks(current=0, best=0)),
        ("Leggere", history.Streaks(current=1, best=1)),
    ]


def test_lo_storico_ha_solo_le_abitudini_attive_dell_utente(sessione, io, altro):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    correre = habits.create_habit(sessione, io.id, "Correre", "boolean")
    spunta(sessione, io, correre, 1, 2)
    habits.archive(sessione, io.id, correre.id)
    sua = habits.create_habit(sessione, altro.id, "Nuotare", "boolean")
    spunta(sessione, altro, sua, 0)

    storico = history.get_history(sessione, io.id, OGGI)

    assert [riga.habit.name for riga in storico] == ["Meditare"]
