"""Fixture per i test di integrazione: un Postgres vero in un container usa e getta."""

import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Engine, create_engine, make_url, text
from sqlalchemy.orm import Session
from testcontainers.community.postgres import PostgresContainer

from daylog.db.models import User

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
