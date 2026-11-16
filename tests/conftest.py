"""Fixture per i test di integrazione: un Postgres vero in un container usa e getta."""

import uuid
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, Engine, create_engine, make_url, text
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from daylog.days import EditWindow
from daylog.db.models import User
from daylog.db.session import get_session
from daylog.deps import get_edit_window, get_today
from daylog.main import app

ALEMBIC_INI = Path(__file__).parent.parent / "alembic.ini"


@pytest.fixture(scope="session")
def postgres() -> URL:
    """Un container postgres:18 (la stessa immagine di compose.yaml) per tutta la sessione."""
    with PostgresContainer("postgres:18", driver="psycopg") as container:
        yield make_url(container.get_connection_url())


def crea_database(server: URL) -> str:
    """Crea un database vuoto con un nome univoco e ne restituisce l'URL."""
    nome = f"test_{uuid.uuid4().hex[:8]}"
    # CREATE DATABASE non può stare dentro una transazione: serve AUTOCOMMIT
    engine = create_engine(server, isolation_level="AUTOCOMMIT")
    with engine.connect() as connessione:
        connessione.execute(text(f'CREATE DATABASE "{nome}"'))
    engine.dispose()
    # str(url) nasconderebbe la password con ***
    return server.set(database=nome).render_as_string(hide_password=False)


def config_alembic(url: str) -> Config:
    config = Config(ALEMBIC_INI)
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config


@pytest.fixture
def config_vuoto(postgres: URL) -> Config:
    """Configurazione di Alembic che punta a un database nuovo e vuoto."""
    return config_alembic(crea_database(postgres))


@pytest.fixture(scope="session")
def engine_migrato(postgres: URL) -> Engine:
    """Un database portato all'ultima migrazione, condiviso da tutti i test."""
    url = crea_database(postgres)
    command.upgrade(config_alembic(url), "head")
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def sessione(engine_migrato: Engine) -> Session:
    """Una sessione dentro una transazione annullata a fine test: i test non si sporcano a vicenda.

    create_savepoint: i commit e i rollback del test diventano SAVEPOINT dentro la transazione
    esterna, quindi anche dopo un IntegrityError il rollback finale cancella tutto.
    """
    with engine_migrato.connect() as connessione:
        transazione = connessione.begin()
        with Session(bind=connessione, join_transaction_mode="create_savepoint") as sessione:
            yield sessione
        transazione.rollback()


@pytest.fixture
def io(sessione: Session) -> User:
    """L'utente dei test."""
    utente = User(email="io@example.com")
    sessione.add(utente)
    sessione.flush()
    return utente


@pytest.fixture
def altro(sessione: Session) -> User:
    """Un secondo utente, per controllare che ognuno veda e modifichi solo le sue cose."""
    utente = User(email="altro@example.com")
    sessione.add(utente)
    sessione.flush()
    return utente


@pytest.fixture
def oggi() -> date:
    """Il giorno in corso nei test: fisso, così i test non dipendono dall'orologio."""
    return date(2026, 11, 16)


@pytest.fixture
def finestra(oggi: date) -> EditWindow:
    """La finestra di modifica di default: da oggi fino a 7 giorni fa."""
    return EditWindow(today=oggi, days=7)


@pytest.fixture
def client(sessione: Session, io: User, oggi: date, finestra: EditWindow) -> TestClient:
    """Il client HTTP dei test, senza lifespan: le route usano sessione, utente e giorno dei test.

    dependency_overrides dice a FastAPI "al posto di questa dependency usa quest'altra".
    Senza commit, quello che scrive una richiesta lo legge la successiva dello stesso test,
    e il rollback della fixture sessione cancella tutto alla fine.
    """
    app.dependency_overrides[get_session] = lambda: sessione
    app.dependency_overrides[get_today] = lambda: oggi
    # Senza lifespan non c'è app.state.edit_window_days
    app.dependency_overrides[get_edit_window] = lambda: finestra
    # L'utente al posto del lifespan: gira la get_user_id vera, che lo segna nella richiesta
    app.state.user_id = io.id
    yield TestClient(app)
    app.dependency_overrides.clear()
    del app.state.user_id
