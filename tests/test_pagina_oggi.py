"""La pagina del giorno, provata via HTTP: stato delle abitudini, nota, finestra e spunte."""

from datetime import timedelta

import pytest

from daylog import days, habits


def test_oggi_mostra_le_abitudini_attive_in_ordine(client, sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    correre = habits.create_habit(sessione, io.id, "Correre", "boolean")
    habits.archive(sessione, io.id, correre.id)

    risposta = client.get("/")

    assert risposta.status_code == 200
    assert risposta.text.index("Meditare") < risposta.text.index("Leggere")
    assert "Correre" not in risposta.text


def test_un_abitudine_si_no_spuntata_compare_come_fatta(client, sessione, io, oggi, finestra):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Stretching", "boolean")
    days.set_check(sessione, io.id, finestra, meditare.id, oggi)

    pagina = client.get("/").text

    assert pagina.count("checked") == 1
    assert pagina.index("Meditare") < pagina.index("checked") < pagina.index("Stretching")


def test_un_abitudine_con_valore_mostra_il_valore_e_l_unita(client, sessione, io, oggi, finestra):
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    days.set_check(sessione, io.id, finestra, lettura.id, oggi, value=30)

    pagina = client.get("/").text

    assert 'value="30"' in pagina
    assert "minuti" in pagina


def test_oggi_mostra_la_nota_del_giorno(client, sessione, io, oggi, finestra):
    days.set_note(sessione, io.id, finestra, oggi, "Dormito poco, ma ho letto")

    assert "Dormito poco, ma ho letto" in client.get("/").text


def test_un_giorno_passato_mostra_le_sue_spunte(client, sessione, io, oggi, finestra):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    tre_giorni_fa = oggi - timedelta(days=3)
    days.set_check(sessione, io.id, finestra, meditare.id, tre_giorni_fa)

    risposta = client.get(f"/days/{tre_giorni_fa.isoformat()}")

    assert risposta.status_code == 200
    assert "checked" in risposta.text
    assert "checked" not in client.get("/").text


def test_un_giorno_nel_futuro_non_esiste(client, oggi):
    domani = oggi + timedelta(days=1)

    assert client.get(f"/days/{domani.isoformat()}").status_code == 404


def test_da_oggi_si_va_a_ieri_ma_non_a_domani(client):
    pagina = client.get("/").text

    assert 'href="/days/2026-11-15"' in pagina
    assert "/days/2026-11-17" not in pagina


def test_da_un_giorno_passato_si_va_al_giorno_dopo(client):
    assert 'href="/days/2026-11-14"' in client.get("/days/2026-11-13").text


def test_da_ieri_il_giorno_dopo_e_oggi(client):
    # Con il testo del link: href="/" da solo c'è anche nel menu di ogni pagina
    assert 'href="/">giorno dopo' in client.get("/days/2026-11-15").text


def test_fuori_dalla_finestra_il_giorno_si_legge_e_basta(client, sessione, io, oggi):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    otto_giorni_fa = oggi - timedelta(days=8)

    fuori = client.get(f"/days/{otto_giorni_fa.isoformat()}").text
    dentro = client.get("/").text

    assert "disabled" in fuori
    assert "non si può più modificare" in fuori
    assert "disabled" not in dentro


def test_spuntare_un_abitudine_si_no_la_segna_come_fatta(client, sessione, io, oggi):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")

    risposta = client.put(f"/days/{oggi.isoformat()}/checks/{meditare.id}")

    assert risposta.status_code == 200
    # Un frammento: solo la riga dell'abitudine, che HTMX mette al posto di quella vecchia
    assert "<html" not in risposta.text
    assert "Meditare" in risposta.text
    [riga] = days.get_day(sessione, io.id, oggi).habits
    assert riga.done


def test_togliere_la_spunta_segna_l_abitudine_come_non_fatta(client, sessione, io, oggi, finestra):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    days.set_check(sessione, io.id, finestra, meditare.id, oggi)

    risposta = client.delete(f"/days/{oggi.isoformat()}/checks/{meditare.id}")

    assert risposta.status_code == 200
    assert "Meditare" in risposta.text
    [riga] = days.get_day(sessione, io.id, oggi).habits
    assert not riga.done


def test_un_abitudine_con_valore_si_spunta_con_il_valore(client, sessione, io, oggi):
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    url = f"/days/{oggi.isoformat()}/checks/{lettura.id}"
    risposta = client.put(url, data={"value": "30"})

    assert risposta.status_code == 200
    assert 'value="30"' in risposta.text
    [riga] = days.get_day(sessione, io.id, oggi).habits
    assert (riga.done, riga.value) == (True, 30)


@pytest.mark.parametrize("valore", ["", "0"], ids=["campo vuoto", "zero"])
def test_senza_un_valore_positivo_la_riga_torna_con_un_errore(client, sessione, io, oggi, valore):
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    url = f"/days/{oggi.isoformat()}/checks/{lettura.id}"
    risposta = client.put(url, data={"value": valore})

    assert risposta.status_code == 422
    assert "Scrivi un numero maggiore di zero" in risposta.text
    [riga] = days.get_day(sessione, io.id, oggi).habits
    assert not riga.done


@pytest.mark.parametrize("metodo", ["PUT", "DELETE"])
def test_fuori_dalla_finestra_le_spunte_non_si_cambiano(client, sessione, io, oggi, metodo):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    otto_giorni_fa = oggi - timedelta(days=8)

    url = f"/days/{otto_giorni_fa.isoformat()}/checks/{meditare.id}"
    risposta = client.request(metodo, url)

    assert risposta.status_code == 403
    [riga] = days.get_day(sessione, io.id, otto_giorni_fa).habits
    assert not riga.done


@pytest.mark.parametrize("metodo", ["PUT", "DELETE"])
def test_la_spunta_di_un_abitudine_di_un_altro_utente_non_si_trova(
    client, sessione, altro, oggi, metodo
):
    sua = habits.create_habit(sessione, altro.id, "Correre", "boolean")

    risposta = client.request(metodo, f"/days/{oggi.isoformat()}/checks/{sua.id}")

    assert risposta.status_code == 404


def test_un_abitudine_si_no_non_si_spunta_con_un_valore(client, sessione, io, oggi):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")

    url = f"/days/{oggi.isoformat()}/checks/{meditare.id}"
    risposta = client.put(url, data={"value": "5"})

    assert risposta.status_code == 422
    assert "si spunta senza valore" in risposta.text
    [riga] = days.get_day(sessione, io.id, oggi).habits
    assert not riga.done


def test_la_nota_si_salva_dal_form(client, sessione, io, oggi):
    url = f"/days/{oggi.isoformat()}/note"
    risposta = client.put(url, data={"text": "Dormito poco, ma ho letto"})

    assert risposta.status_code == 200
    assert "<html" not in risposta.text
    assert "Salvata" in risposta.text
    assert days.get_day(sessione, io.id, oggi).note == "Dormito poco, ma ho letto"


def test_svuotare_la_nota_la_cancella(client, sessione, io, oggi, finestra):
    days.set_note(sessione, io.id, finestra, oggi, "Da cancellare")

    risposta = client.put(f"/days/{oggi.isoformat()}/note", data={"text": ""})

    assert risposta.status_code == 200
    assert days.get_day(sessione, io.id, oggi).note is None


def test_fuori_dalla_finestra_la_nota_non_si_cambia(client, sessione, io, oggi):
    otto_giorni_fa = oggi - timedelta(days=8)

    url = f"/days/{otto_giorni_fa.isoformat()}/note"
    risposta = client.put(url, data={"text": "Troppo tardi"})

    assert risposta.status_code == 403
    assert days.get_day(sessione, io.id, otto_giorni_fa).note is None


def test_senza_abitudini_oggi_dice_come_cominciare(client, sessione, io):
    assert "Nessuna abitudine ancora" in client.get("/").text

    habits.create_habit(sessione, io.id, "Meditare", "boolean")

    assert "Nessuna abitudine ancora" not in client.get("/").text
