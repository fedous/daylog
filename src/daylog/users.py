"""Gli utenti: in fase 2 uno solo, cercato o creato all'avvio dall'email."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from daylog.db.models import User


def get_or_create(session: Session, email: str) -> User:
    """L'utente con questa email; se non c'è ancora, lo crea.

    L'email si salva senza spazi ai lati e in minuscolo: "Io@Example.com" è lo stesso utente.
    """
    email = email.strip().lower()
    user = session.scalar(select(User).where(User.email == email))
    if user is not None:
        return user
    user = User(email=email)
    session.add(user)
    session.flush()
    return user
