"""La PWA: quello che il server promette al browser per installare daylog e usarlo offline.

Il JavaScript del service worker non gira in pytest: il suo comportamento si prova a mano
in Chrome (DevTools → Application, Network → Offline).
"""

import json
import re
import struct

import pytest

MANIFEST = "/static/manifest.webmanifest"


def misura_png(dati: bytes) -> str:
    """La misura scritta nell'intestazione di un PNG, nel formato del manifest (es. "192x192").

    Un PNG inizia con 8 byte fissi, poi il blocco IHDR: 4 byte di lunghezza, 4 con "IHDR",
    poi larghezza e altezza come interi a 32 bit big-endian.
    """
    assert dati[:8] == b"\x89PNG\r\n\x1a\n"
    assert dati[12:16] == b"IHDR"
    larghezza, altezza = struct.unpack(">II", dati[16:24])
    return f"{larghezza}x{altezza}"


def lista_precache(client) -> list[str]:
    """La lista PRECACHE di sw.js: gli URL che il service worker scarica all'installazione."""
    sw = client.get("/sw.js").text
    trovata = re.search(r"const PRECACHE = (\[.*?\]);", sw, re.DOTALL)
    assert trovata, "manca const PRECACHE = [...]; in sw.js"
    return json.loads(trovata.group(1))


def test_il_manifest_descrive_daylog_come_app_a_schermo_intero(client):
    risposta = client.get(MANIFEST)

    assert risposta.status_code == 200
    assert risposta.headers["content-type"] == "application/manifest+json"
    manifest = risposta.json()
    assert manifest["name"] == "daylog"
    assert manifest["short_name"] == "daylog"
    assert manifest["lang"] == "it"
    # Si apre su "oggi" e controlla tutto il sito
    assert manifest["start_url"] == "/"
    assert manifest["scope"] == "/"
    # L'identità dell'app installata: resta la stessa anche se un giorno cambia start_url
    assert manifest["id"] == "/"
    # Senza la barra del browser
    assert manifest["display"] == "standalone"
    # Il blu primario di Pico e il suo sfondo chiaro
    assert manifest["theme_color"] == "#0172ad"
    assert manifest["background_color"] == "#ffffff"


def test_il_manifest_ha_le_icone_che_chiede_android(client):
    icone = client.get(MANIFEST).json()["icons"]

    misure = {(icona["sizes"], icona.get("purpose", "any")) for icona in icone}
    assert {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= misure


def test_ogni_icona_del_manifest_e_un_png_della_misura_dichiarata(client):
    icone = client.get(MANIFEST).json()["icons"]

    for icona in icone:
        risposta = client.get(icona["src"])
        assert risposta.status_code == 200, icona["src"]
        assert risposta.headers["content-type"] == "image/png"
        assert icona["type"] == "image/png"
        assert misura_png(risposta.content) == icona["sizes"], icona["src"]


def test_il_service_worker_e_servito_dalla_radice_senza_cache(client):
    # Dalla radice il suo scope è tutto il sito; da /static/ controllerebbe solo /static/
    risposta = client.get("/sw.js")

    assert risposta.status_code == 200
    assert risposta.headers["content-type"].startswith("text/javascript")
    # Il browser chiede ogni volta al server se sw.js è cambiato: gli aggiornamenti arrivano subito
    assert risposta.headers["cache-control"] == "no-cache"


def test_ogni_url_che_il_service_worker_mette_in_cache_esiste(client):
    # All'installazione il service worker scarica la lista PRECACHE con cache.addAll():
    # basta un 404 e l'installazione fallisce tutta, senza avvisi nella pagina
    precache = lista_precache(client)

    assert precache
    for url in precache:
        assert client.get(url).status_code == 200, url


@pytest.mark.parametrize("pagina", ["/", "/habits", "/history"])
def test_ogni_pagina_collega_il_manifest_e_registra_il_service_worker(client, pagina):
    testo = client.get(pagina).text

    assert f'<link rel="manifest" href="{MANIFEST}">' in testo
    # Il colore della barra di stato di Android, lo stesso del manifest
    assert '<meta name="theme-color" content="#0172ad">' in testo
    assert 'navigator.serviceWorker.register("/sw.js")' in testo


def test_la_pagina_offline_dice_che_manca_la_rete_e_ha_il_menu(client):
    # Il service worker la mostra al posto di una pagina quando la rete non c'è
    risposta = client.get("/offline")

    assert risposta.status_code == 200
    assert "<h1>Sei offline</h1>" in risposta.text
    for link in ['href="/"', 'href="/habits"', 'href="/history"']:
        assert link in risposta.text


def test_il_service_worker_ha_gia_in_cache_la_pagina_offline(client):
    # Senza, la prima volta senza rete non avrebbe niente da mostrare
    assert "/offline" in lista_precache(client)
