"""Business logic del riepilogo pubblico del dataset (freschezza dei dati).

Il service orchestra i repository e non fa SQL; la regola di dominio della
freschezza (`is_stale`) vive qui e solo qui: l'app si limita a mostrarla.
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.repositories import cinema_repo, showing_repo


def _as_utc(moment: datetime) -> datetime:
    """Interpreta un datetime come UTC, anche se arriva naive da SQLite.

    `func.now()` in SQLite produce un datetime naive in UTC: restituito così
    com'è, l'app lo leggerebbe come ora locale (due ore di errore in estate).
    Il fuso si gestisce qui, al confine del dominio: fuori esce solo ISO con offset.
    """
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment


def get_dataset_info(db: Session) -> dict:
    """Riepilogo pubblico: quanti dati ci sono e quanto sono vecchi.

    ⚠️ Fonte del timestamp (limite noto): `max(Showing.scraped_at)` è l'istante
    in cui la riga più recente è stata **inserita**, non l'istante della run di
    scraping che ha prodotto i dati (`showing_repo.upsert` non aggiorna
    `scraped_at` sulle righe esistenti). La semantica desiderata — «istante
    della run che ha prodotto i dati oggi nel DB» — richiede il `generated_at`
    dei JSON persistito dal seed (evoluzione `dataset_meta`, vedi
    docs/backend/api.md §4.10 e docs/problemi-aperti.md).

    Ritorna un dict nuovo (nessuna mutazione) con i campi dello schema
    `DatasetInfo`: `latest_scraped_at` (ISO con offset UTC), `age_hours`,
    `is_stale`, `stale_after_hours`, `showings`, `cinemas`.
    """
    settings = get_settings()
    stale_after_hours = settings.dataset_stale_after_hours

    latest = showing_repo.latest_scraped_at(db)
    latest_utc = _as_utc(latest) if latest is not None else None

    age_hours: float | None = None
    if latest_utc is not None:
        age_hours = round((datetime.now(UTC) - latest_utc).total_seconds() / 3600, 2)

    # Un DB vuoto è stale quanto uno vecchio: "nessun dato" non è "dati freschi".
    is_stale = age_hours is None or age_hours > stale_after_hours

    return {
        "latest_scraped_at": latest_utc.isoformat() if latest_utc else None,
        "age_hours": age_hours,
        "is_stale": is_stale,
        "stale_after_hours": stale_after_hours,
        "showings": showing_repo.count_all(db),
        "cinemas": cinema_repo.count_all(db),
    }
