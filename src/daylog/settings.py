from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurazione letta dalle variabili d'ambiente (es. DATABASE_URL) o dal file .env."""

    model_config = SettingsConfigDict(env_file=".env")

    # Default: il Postgres di compose.yaml. In produzione arriva da DATABASE_URL.
    database_url: str = "postgresql+psycopg://daylog:daylog@127.0.0.1:5432/daylog"
