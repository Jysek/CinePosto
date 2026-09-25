"""Settings centralizzate caricate da .env (pydantic-settings)."""

from functools import lru_cache
import os
from pathlib import Path

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default CORS per sviluppo locale (Expo dev server, Metro bundler, web build).
# In produzione vengono sovrascritti da CORS_ORIGINS nel .env.
_DEV_CORS_DEFAULTS = [
    "http://localhost:8081",  # Metro bundler
    "http://localhost:8090",  # Metro, quando la 8081 è occupata (make dev)
    "http://localhost:19006",  # Expo web
    "http://localhost:3000",  # test web occasionale
]


class Settings(BaseSettings):
    """Configurazione dell'applicazione, letta da variabili d'ambiente e file .env.

    Ogni campo ha un default dev-friendly: il backend parte anche senza .env.
    In produzione i valori vanno espliciti (vedi .env.example per il formato:
    CORS_ORIGINS deve essere un array JSON, non CSV — limite di pydantic-settings 2.6).
    """

    # pydantic-settings: legge automaticamente i valori dal file .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    log_level: str = "INFO"

    # DB: default dev-friendly (SQLite locale). In prod si passa via .env.
    database_url: str = "sqlite:///./cineposto.db"

    # Path del JSON scraper. Relativo alla cartella backend/ di default;
    # viene risolto a path assoluto al load, cosi' non dipende dalla CWD.
    scraper_output_dir: Path = Path("../scraper/output")

    # Archiviazione dei residui del seed (soft delete con `removed_at`): le righe non
    # piu' nei JSON dell'ultima importazione si marcano come fuori programmazione,
    # mai si cancellano (decisione dell'utente: i dati storici si conservano).
    seed_archive_enabled: bool = True
    # Guardia anti-fonte-rotta: se per un cinema gli showings importati sono meno di
    # `seed_archive_min_ratio` di quelli gia' nel DB per la stessa finestra, sembra una
    # fonte andata a metà e non una programmazione cambiata: l'archiviazione si salta.
    seed_archive_min_ratio: float = 0.5

    # CORS: se .env non specifica CORS_ORIGINS, usa i default dev.
    cors_origins: list[str] = Field(default_factory=lambda: list(_DEV_CORS_DEFAULTS))

    # ADMIN TOKEN: nessun default insicuro. In sviluppo, se .env non lo setta, viene
    # generato un token random per il processo; in produzione la sua assenza è un errore.
    admin_token: str = ""

    @field_validator("scraper_output_dir", mode="after")
    @classmethod
    def _resolve_scraper_dir(cls, v: Path) -> Path:
        """Risolve il path a assoluto al load: il seed non dipende dalla CWD di lancio."""
        return v.expanduser().resolve()

    @field_validator("admin_token", mode="after")
    @classmethod
    def _generate_admin_token_if_empty(cls, v: str, info: ValidationInfo) -> str:
        """Garantisce un token admin presente e mai banale, senza mai stamparlo in produzione.

        Sviluppo: se .env non lo imposta (o contiene il placeholder), viene generato un token
        random e stampato **una volta** all'avvio, così gli endpoint admin restano protetti
        anche su un'installazione non configurata.
        Produzione: nessun token a runtime — se manca, il processo non parte. Un segreto
        stampato nei log di produzione è un segreto bruciato (journald, aggregatori, backup).
        """
        if v and v != "change-me-before-deploy":
            return v

        env = str(info.data.get("env") or os.environ.get("ENV") or "development")
        if env == "production":
            raise ValueError(
                "ADMIN_TOKEN è obbligatorio con ENV=production: "
                'genera un token con `python -c "import secrets; print(secrets.token_urlsafe(32))"` '
                "e mettilo in .env"
            )

        import secrets

        generated = secrets.token_urlsafe(32)
        print(
            f"⚠️  ADMIN_TOKEN non configurato in .env — generato al volo:\n"
            f"    {generated}\n"
            f"    (imposta ADMIN_TOKEN=... in .env per averlo stabile)"
        )
        return generated


@lru_cache
def get_settings() -> Settings:
    """Singleton delle Settings: il .env viene letto una volta sola per processo."""
    return Settings()
