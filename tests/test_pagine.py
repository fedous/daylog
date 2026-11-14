from fastapi.testclient import TestClient

from daylog.main import app

client = TestClient(app)


def test_la_home_mostra_daylog_e_carica_htmx():
    risposta = client.get("/")

    assert risposta.status_code == 200
    assert risposta.headers["content-type"].startswith("text/html")
    assert "<title>daylog</title>" in risposta.text
    assert '<script src="/static/htmx.min.js"' in risposta.text


def test_htmx_viene_servito_come_file_statico():
    risposta = client.get("/static/htmx.min.js")

    assert risposta.status_code == 200
    assert "javascript" in risposta.headers["content-type"]
    assert risposta.text.startswith("var htmx=")
