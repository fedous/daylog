from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

CARTELLA = Path(__file__).parent

app = FastAPI(title="daylog")
app.mount("/static", StaticFiles(directory=CARTELLA / "static"), name="static")
templates = Jinja2Templates(directory=CARTELLA / "templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "home.html")
