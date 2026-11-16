"""La pagina dello storico: serie in corso e record di ogni abitudine attiva."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from daylog import history
from daylog.deps import SessionDep, TodayDep, UserIdDep
from daylog.web import templates

router = APIRouter()


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request, session: SessionDep, user_id: UserIdDep, today: TodayDep):
    rows = history.get_history(session, user_id, today)
    return templates.TemplateResponse(request, "history.html", {"rows": rows})
