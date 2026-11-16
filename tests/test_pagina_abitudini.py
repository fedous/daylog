"""La pagina delle abitudini, provata via HTTP: quello che mostra, i form e gli errori."""

import pytest

from daylog import habits


def test_la_pagina_mostra_le_abitudini_attive_in_ordine(client, sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    risposta = client.get("/habits")

    assert risposta.status_code == 200
    assert risposta.text.index("Meditare") < risposta.text.index("Leggere")


def test_le_archiviate_stanno_in_una_sezione_a_parte(client, sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    correre = habits.create_habit(sessione, io.id, "Correre", "boolean")
    habits.archive(sessione, io.id, correre.id)

    pagina = client.get("/habits").text

    assert pagina.index("Meditare") < pagina.index("Archiviate") < pagina.index("Correre")


def test_un_abitudine_creata_dal_form_compare_nella_pagina(client):
    dati = {"name": "Leggere", "kind": "quantity", "unit": "minuti"}

    risposta = client.post("/habits", data=dati, follow_redirects=False)

    assert risposta.status_code == 303
    assert risposta.headers["location"] == "/habits"
    assert "Leggere" in client.get("/habits").text


def test_un_abitudine_si_no_si_crea_anche_con_il_campo_unita_vuoto(client):
    # Il browser manda anche gli input lasciati vuoti, con valore ""
    dati = {"name": "Meditare", "kind": "boolean", "unit": ""}

    risposta = client.post("/habits", data=dati)

    assert risposta.status_code == 200
    assert "Meditare" in risposta.text


# Ogni form riceve la vecchia "Meditare" archiviata e "Leggere", e dà (url, dati)
FORM_CON_NOME_DOPPIO = {
    "creare": lambda vecchia, lettura: ("/habits", {"name": "meditare", "kind": "boolean"}),
    "rinominare": lambda vecchia, lettura: (f"/habits/{lettura.id}", {"name": "meditare"}),
    "ripristinare": lambda vecchia, lettura: (f"/habits/{vecchia.id}/restore", {}),
}


@pytest.mark.parametrize("form", FORM_CON_NOME_DOPPIO.values(), ids=FORM_CON_NOME_DOPPIO.keys())
def test_con_un_nome_doppio_la_pagina_torna_con_un_errore(client, sessione, io, form):
    vecchia = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.archive(sessione, io.id, vecchia.id)
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    url, dati = form(vecchia, lettura)

    risposta = client.post(url, data=dati)

    assert risposta.status_code == 422
    assert "è già usato" in risposta.text


# Ogni form riceve "Leggere", e dà (url, dati)
FORM_CON_NOME_VUOTO = {
    "creare": lambda lettura: ("/habits", {"name": "   ", "kind": "boolean"}),
    "rinominare": lambda lettura: (f"/habits/{lettura.id}", {"name": "   "}),
}


@pytest.mark.parametrize("form", FORM_CON_NOME_VUOTO.values(), ids=FORM_CON_NOME_VUOTO.keys())
def test_con_un_nome_vuoto_la_pagina_torna_con_un_errore(client, sessione, io, form):
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    url, dati = form(lettura)

    risposta = client.post(url, data=dati)

    assert risposta.status_code == 422
    assert "Il nome non può essere vuoto" in risposta.text


def test_un_abitudine_si_rinomina_e_le_si_cambia_l_unita_dal_form(client, sessione, io):
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")
    dati = {"name": "Leggere libri", "unit": "pagine"}

    risposta = client.post(f"/habits/{lettura.id}", data=dati, follow_redirects=False)

    assert risposta.status_code == 303
    pagina = client.get("/habits").text
    assert "Leggere libri" in pagina
    assert "pagine" in pagina


def test_un_abitudine_archiviata_dal_pulsante_passa_tra_le_archiviate(client, sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    correre = habits.create_habit(sessione, io.id, "Correre", "boolean")

    risposta = client.post(f"/habits/{correre.id}/archive", follow_redirects=False)

    assert risposta.status_code == 303
    pagina = client.get("/habits").text
    assert pagina.index("Meditare") < pagina.index("Archiviate") < pagina.index("Correre")


def test_un_abitudine_ripristinata_dal_pulsante_torna_in_fondo_alle_attive(client, sessione, io):
    correre = habits.create_habit(sessione, io.id, "Correre", "boolean")
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.archive(sessione, io.id, correre.id)

    risposta = client.post(f"/habits/{correre.id}/restore", follow_redirects=False)

    assert risposta.status_code == 303
    pagina = client.get("/habits").text
    assert "Archiviate" not in pagina
    assert pagina.index("Meditare") < pagina.index("Correre")


def test_il_pulsante_su_sposta_l_abitudine_di_un_posto(client, sessione, io):
    habits.create_habit(sessione, io.id, "Meditare", "boolean")
    lettura = habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    url = f"/habits/{lettura.id}/move"
    risposta = client.post(url, data={"direction": "up"}, follow_redirects=False)

    assert risposta.status_code == 303
    pagina = client.get("/habits").text
    assert pagina.index("Leggere") < pagina.index("Meditare")


def test_una_direzione_sconosciuta_non_sposta_niente(client, sessione, io):
    meditare = habits.create_habit(sessione, io.id, "Meditare", "boolean")
    habits.create_habit(sessione, io.id, "Leggere", "quantity", unit="minuti")

    risposta = client.post(f"/habits/{meditare.id}/move", data={"direction": "su"})

    assert risposta.status_code == 422
    pagina = client.get("/habits").text
    assert pagina.index("Meditare") < pagina.index("Leggere")


# Ogni form riceve l'id dell'abitudine, e dà (url, dati)
FORM_SU_UN_ABITUDINE = {
    "rinominare": lambda habit_id: (f"/habits/{habit_id}", {"name": "Mia"}),
    "archiviare": lambda habit_id: (f"/habits/{habit_id}/archive", {}),
    "ripristinare": lambda habit_id: (f"/habits/{habit_id}/restore", {}),
    "spostare": lambda habit_id: (f"/habits/{habit_id}/move", {"direction": "up"}),
}


@pytest.mark.parametrize("form", FORM_SU_UN_ABITUDINE.values(), ids=FORM_SU_UN_ABITUDINE.keys())
def test_un_abitudine_di_un_altro_utente_non_si_trova(client, sessione, altro, form):
    sua = habits.create_habit(sessione, altro.id, "Correre", "boolean")
    url, dati = form(sua.id)

    risposta = client.post(url, data=dati)

    assert risposta.status_code == 404
