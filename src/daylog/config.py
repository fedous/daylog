from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurazione letta dalle variabili d'ambiente o dal file .env.

    Le variabili di daylog hanno il prefisso DAYLOG_ (es. DAYLOG_USER_EMAIL), tranne DATABASE_URL,
    il nome che usano le piattaforme gestite. I default sono quelli dello sviluppo in locale.
    """

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DAYLOG_")

    # Il Postgres di compose.yaml. Con un alias il prefisso non si applica.
    database_url: str = Field(
        default="postgresql+psycopg://daylog:daylog@127.0.0.1:5432/daylog",
        validation_alias="DATABASE_URL",
    )
    # In fase 2 l'utente è uno solo, cercato o creato all'avvio (ADR-0008)
    user_email: str = "io@example.com"
    # Fino a quanti giorni fa si cambiano spunte e note
    edit_window_days: int = Field(default=7, ge=0)
