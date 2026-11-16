import pytest


def test_la_home_mostra_daylog_e_carica_htmx(client):
    risposta = client.get("/")

    assert risposta.status_code == 200
    assert risposta.headers["content-type"].startswith("text/html")
    assert "<title>daylog</title>" in risposta.text
    assert '<script src="/static/htmx.min.js"' in risposta.text


def test_htmx_viene_servito_come_file_statico(client):
    risposta = client.get("/static/htmx.min.js")

    assert risposta.status_code == 200
    assert "javascript" in risposta.headers["content-type"]
    assert risposta.text.startswith("var htmx=")


def test_la_home_carica_pico_e_poi_il_nostro_css(client):
    pagina = client.get("/").text

    pico = pagina.index('<link rel="stylesheet" href="/static/pico.classless.min.css">')
    nostro = pagina.index('<link rel="stylesheet" href="/static/style.css">')
    # Il nostro va dopo: a parità di selettore vince l'ultima regola letta
    assert pico < nostro


@pytest.mark.parametrize("file", ["pico.classless.min.css", "style.css"])
def test_i_css_vengono_serviti_come_file_statici(client, file):
    risposta = client.get(f"/static/{file}")

    assert risposta.status_code == 200
    assert risposta.headers["content-type"].startswith("text/css")


@pytest.mark.parametrize("pagina", ["/", "/habits", "/history"])
def test_ogni_pagina_ha_il_menu_verso_le_altre(client, pagina):
    testo = client.get(pagina).text

    for link in ['href="/"', 'href="/habits"', 'href="/history"']:
        assert link in testo
