from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session


def get_session(request: Request) -> Generator[Session]:
    """Una sessione per richiesta: commit se la route finisce bene, rollback se lancia un'eccezione.

    L'engine lo crea il lifespan all'avvio. session.begin() fa da solo commit o rollback
    all'uscita del blocco with.
    """
    with Session(request.app.state.engine) as session, session.begin():
        yield session
