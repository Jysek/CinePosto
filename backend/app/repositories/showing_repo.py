"""Data access layer: query su Showing (spettacoli)."""

from datetime import date as date_type

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.film import Film
from app.models.showing import Showing


def _active_only() -> tuple[ColumnElement[bool], ...]:
    """Condizioni di visibilità condivise dalle letture pubbliche.

    Uno spettacolo conta solo se è attivo (non archiviato) **e** il suo film è
    attivo: gli showings di un film archiviato non devono comparire, nemmeno
    quelli fuori finestra che l'archiviazione non tocca perché sono storia.
    """
    return (Showing.removed_at.is_(None), Showing.film.has(Film.removed_at.is_(None)))


def get_by_id(db: Session, showing_id: int) -> Showing | None:
    """Ritorna lo spettacolo con la PK data, o None se non esiste."""
    return db.get(Showing, showing_id)


def list_by_date(db: Session, target_date: date_type) -> list[Showing]:
    """Tutti gli spettacoli di una data specifica, con Film e Cinema pre-caricati.
    Il `joinedload` evita il classico problema N+1: senza, l'ORM farebbe
    1 query per la lista + N query per caricare cinema e film di ognuno.
    Con joinedload → 1 query JOIN sola.
    """
    stmt = (
        select(Showing)
        .options(joinedload(Showing.film), joinedload(Showing.cinema))
        .where(*_active_only(), Showing.date == target_date)
        .order_by(Showing.date)
    )
    return list(db.scalars(stmt))


def list_by_date_range(db: Session, date_from: date_type, date_to: date_type) -> list[Showing]:
    """Spettacoli nel range di date (estremi inclusi), con Film e Cinema pre-caricati."""
    stmt = (
        select(Showing)
        .options(joinedload(Showing.film), joinedload(Showing.cinema))
        .where(*_active_only(), Showing.date >= date_from, Showing.date <= date_to)
        .order_by(Showing.date)
    )
    return list(db.scalars(stmt))


def list_by_cinema_in_range(db: Session, cinema_slug: str, date_from: date_type, date_to: date_type) -> list[Showing]:
    """Programmazione di un singolo cinema nel range di date (estremi inclusi).

    Eager loading del solo Film: il Cinema è già noto al chiamante (è il filtro).
    """
    stmt = (
        select(Showing)
        .options(joinedload(Showing.film))  # solo film, cinema noto
        .where(
            *_active_only(),
            Showing.cinema_slug == cinema_slug,
            Showing.date >= date_from,
            Showing.date <= date_to,
        )
        .order_by(Showing.date)
    )
    return list(db.scalars(stmt))


def list_by_film(db: Session, film_id: int, from_date: date_type) -> list[Showing]:
    """Prossimi spettacoli di un dato film a partire da una data. Include cinema."""
    stmt = (
        select(Showing)
        .options(joinedload(Showing.cinema))
        .where(*_active_only(), Showing.film_id == film_id, Showing.date >= from_date)
        .order_by(Showing.date)
    )
    return list(db.scalars(stmt))


def count_by_cinema(db: Session, cinema_slug: str) -> int:
    """Numero di spettacoli attivi (futuri) per un cinema. Usato in CinemaWithCount."""
    # COUNT eseguito dal DB: evita di caricare tutte le righe solo per contarle
    stmt = (
        select(func.count())
        .select_from(Showing)
        .where(
            *_active_only(),
            Showing.cinema_slug == cinema_slug,
            Showing.date >= date_type.today(),
        )
    )
    return db.scalar(stmt)


def count_active_in_window(db: Session, cinema_slug: str, date_from: date_type, date_to: date_type) -> int:
    """Showings non archiviati del cinema nella finestra. Serve alla guardia del seed.

    Conta solo gli attivi: sono le sole righe che l'archiviazione potrebbe toccare,
    quindi sono il denominatore onesto del ratio importati/esistenti.
    """
    stmt = (
        select(func.count())
        .select_from(Showing)
        .where(
            Showing.cinema_slug == cinema_slug,
            Showing.date >= date_from,
            Showing.date <= date_to,
            Showing.removed_at.is_(None),
        )
    )
    return db.scalar(stmt)


def upsert(db: Session, data: dict) -> Showing:
    """Insert or update per Showing. Usato dal seed.
    UNIQUE key = (film_id, cinema_slug, date).
    """
    stmt = select(Showing).where(
        Showing.film_id == data["film_id"],
        Showing.cinema_slug == data["cinema_slug"],
        Showing.date == data["date"],
    )
    showing = db.scalars(stmt).one_or_none()

    if showing is None:
        showing = Showing(**data)
        db.add(showing)
    else:
        # Aggiorna orari, lingua, sala, url — questi cambiano tra scraping.
        for key in ("times", "language", "screen", "buy_url"):
            if key in data:
                setattr(showing, key, data[key])

    db.flush()
    return showing


def archive_not_in(
    db: Session,
    cinema_slug: str,
    date_from: date_type,
    date_to: date_type,
    keep_keys: set[tuple[int, date_type]],
) -> int:
    """Archivia gli showings del cinema nella finestra non presenti fra quelli importati.

    `keep_keys` sono le coppie (film_id, date) arrivate dai JSON; tutto ciò che
    nella finestra non è fra quelle è un residuo di run passate e si archivia
    (`removed_at = now`, soft delete — mai DELETE). Fuori finestra non si tocca
    nulla: sono storia.
    """
    rows = list(
        db.scalars(
            select(Showing).where(
                Showing.cinema_slug == cinema_slug,
                Showing.date >= date_from,
                Showing.date <= date_to,
                Showing.removed_at.is_(None),
            )
        )
    )
    archived = 0
    for showing in rows:
        if (showing.film_id, showing.date) not in keep_keys:
            showing.removed_at = func.now()
            archived += 1
    return archived


def reactivate_in(
    db: Session,
    cinema_slug: str,
    date_from: date_type,
    date_to: date_type,
    keep_keys: set[tuple[int, date_type]],
) -> int:
    """Riattiva gli showings archiviati che ricompaiono fra quelli importati.

    `removed_at` torna NULL: lo spettacolo torna in programmazione con i suoi dati.
    """
    rows = list(
        db.scalars(
            select(Showing).where(
                Showing.cinema_slug == cinema_slug,
                Showing.date >= date_from,
                Showing.date <= date_to,
                Showing.removed_at.is_not(None),
            )
        )
    )
    reactivated = 0
    for showing in rows:
        if (showing.film_id, showing.date) in keep_keys:
            showing.removed_at = None
            reactivated += 1
    return reactivated
