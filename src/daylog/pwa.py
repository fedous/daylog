"""La PWA: il service worker servito dalla radice del sito e la pagina offline."""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse

from daylog.web import CARTELLA, templates

router = APIRouter()


@router.get("/sw.js", include_in_schema=False)
def service_worker() -> FileResponse:
    """Un service worker controlla solo le pagine sotto il suo percorso: da qui, tutto il sito."""
    return FileResponse(
        CARTELLA / "static" / "sw.js",
        media_type="text/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/offline", response_class=HTMLResponse, include_in_schema=False)
def offline(request: Request):
    """Niente database né utente: il service worker la scarica una volta e la tiene in cache."""
    return templates.TemplateResponse(request, "offline.html")
