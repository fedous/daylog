"""Quello che serve a tutte le pagine: i template Jinja2."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

CARTELLA = Path(__file__).parent

templates = Jinja2Templates(directory=CARTELLA / "templates")
