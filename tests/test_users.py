"""Gli utenti: in fase 2 uno solo, cercato o creato all'avvio dall'email."""

from daylog import users


def test_la_prima_volta_l_utente_viene_creato_con_la_sua_email(sessione):
    utente = users.get_or_create(sessione, "io@example.com")

    assert utente.id is not None
    assert utente.email == "io@example.com"


def test_la_seconda_volta_restituisce_lo_stesso_utente(sessione):
    primo = users.get_or_create(sessione, "io@example.com")

    secondo = users.get_or_create(sessione, "io@example.com")

    assert secondo.id == primo.id


def test_l_email_si_salva_senza_spazi_e_in_minuscolo_e_indica_lo_stesso_utente(sessione):
    primo = users.get_or_create(sessione, "  Io@Example.COM ")

    secondo = users.get_or_create(sessione, "io@example.com")

    assert primo.email == "io@example.com"
    assert secondo.id == primo.id
