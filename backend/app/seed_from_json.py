"""Seed del database dai JSON prodotti dallo scraper.

Ordine di esecuzione (vincoli di FK):
1. cinemas.json  -> upsert per slug
2. films.json    -> upsert per (title_normalized, year), costruisci lookup {titolo_str_JSON: id_int_DB}
3. showings.json -> risolvi film_id (stringa) -> id (intero) via lookup; upsert per UNIQUE(film_id, cinema_slug, date)
4. riconciliazione -> le righe non più nei JSON dell'ultima importazione si ARCHIVIANO
   (`removed_at`), quelle che ricompaiono si riattivano. Mai DELETE: il DB conserva
   lo storico (decisione dell'utente, 2026-09-25).

Puo' essere eseguito:
- come script standalone: `python -m app.seed_from_json`
- via endpoint admin: POST /api/v1/admin/reimport
"""

from __future__ import annotations

from datetime import date, datetime
import json
import logging
from pathlib import Path
import re

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.maintenance.migrate_removed_at import ensure_removed_at_columns
from app.models import Cinema, Film, Showing  # noqa: F401
from app.repositories import cinema_repo, film_repo, showing_repo

logger = logging.getLogger(__name__)


def _parse_duration(raw: str | int | None) -> int | None:
    """Estrae i minuti da una duration tipo '109 min' o 109 (int).
    Ritorna None se non ci sono numeri riconoscibili.
    """
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    match = re.search(r"(\d+)", str(raw))
    return int(match.group(1)) if match else None


def _load_json(path: Path) -> dict:
    """Carica un JSON dello scraper; errore esplicito se il file manca.

    FileNotFoundError con path completo invece di un generico errore a valle:
    il file mancante è il failure mode più comune (scraper non ancora girato).
    """
    if not path.exists():
        raise FileNotFoundError(f"File JSON dello scraper mancante: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _seed_cinemas(db: Session, data: dict) -> int:
    """Upsert dei cinema. Ritorna il numero di record processati."""
    count = 0
    for entry in data.get("cinemas", []):
        cinema_repo.upsert(
            db,
            {
                "slug": entry["slug"],
                "name": entry["name"],
                "city": entry["city"],
                "address": entry["address"],
                "region": entry.get("region", "Umbria"),
                "lat": entry["lat"],
                "lon": entry["lon"],
                "website": entry.get("website"),
                "phone": entry.get("phone"),
            },
        )
        count += 1
    return count


def _seed_films(db: Session, data: dict) -> tuple[int, dict[str, int], set[tuple[str, int | None]]]:
    """Upsert dei film. Ritorna (numero, lookup titolo_JSON -> id_DB, chiavi importate).

    Il JSON dello scraper usa il TITOLO come chiave; il DB usa un id intero.
    Costruiamo un dizionario di mappatura che sara' usato dal seed di showings
    per risolvere le FK. Le `chiavi importate` sono le chiavi naturali delle righe
    toccate dall'upsert (dopo l'upsert: se una riga ha adottato l'anno, la sua
    chiave reale è quella): sono l'elenco del "tenuto" per l'archiviazione.
    """
    lookup: dict[str, int] = {}
    keep_keys: set[tuple[str, int | None]] = set()
    count = 0
    for entry in data.get("films", []):
        # Il JSON scraper usa 'poster' invece che 'poster_url'.
        # 'genres' arriva come lista Python: la serializziamo in CSV per il model String.
        genres_raw = entry.get("genres")
        if isinstance(genres_raw, list):
            genres_csv = ",".join(str(g) for g in genres_raw) if genres_raw else None
        else:
            genres_csv = genres_raw

        # Il JSON scraper usa 'duration' (stringa "109 min"); qui ricaviamo il numero.
        runtime = _parse_duration(entry.get("duration") or entry.get("runtime_minutes"))

        payload = {
            "title": entry["title"],
            "original_title": entry.get("original_title"),
            "year": entry.get("year"),  # da Wikidata P577; null se il film non è stato arricchito
            "runtime_minutes": runtime,
            "genres": genres_csv,
            "director": entry.get("director"),
            "poster_url": entry.get("poster") or entry.get("poster_url"),
            "synopsis": entry.get("synopsis") or entry.get("description"),
            "wikidata_id": entry.get("wikidata_id"),  # null se il film non è su Wikidata
        }
        film = film_repo.upsert_from_scraper(db, payload)
        # entry['id'] e' il TITOLO stringa nel JSON scraper; lo usiamo come chiave.
        json_key = entry.get("id") or entry["title"]
        lookup[json_key] = film.id
        keep_keys.add((film.title_normalized, film.year))
        count += 1
    return count, lookup, keep_keys


def _seed_showings(
    db: Session, data: dict, film_lookup: dict[str, int]
) -> tuple[int, dict[str, set[tuple[int, date]]]]:
    """Upsert degli spettacoli, UNENDO gli orari per (film, cinema, data).

    Lo scraper puo' emettere piu' record per lo stesso (film, cinema, data) —
    tipicamente uno per sala (es. The Space: Odissea in 7 sale). Il DB pero' ha
    UNIQUE(film_id, cinema_slug, date): senza pre-aggregazione l'upsert terrebbe
    solo l'ultima sala, perdendo tutti gli altri orari. Qui li uniamo in un'unica
    riga. `screen` si conserva solo se proviene da un'unica sala (altrimenti e'
    ambiguo e viene omesso). Salta le righe orfane (film_id JSON non trovato).

    Ritorna (numero, chiavi importate per cinema) con le coppie (film_id, date) che
    servono alla riconciliazione: per ogni cinema sono il "tenuto" di questa run.
    """
    aggregated: dict[tuple, dict] = {}
    keys_by_cinema: dict[str, set[tuple[int, date]]] = {}
    skipped = 0
    for entry in data.get("showings", []):
        film_key = entry["film_id"]
        film_id = film_lookup.get(film_key)
        if film_id is None:
            skipped += 1
            logger.warning("Showing orfano (film JSON non trovato): %s", film_key)
            continue

        # Parsing data
        date_raw = entry["date"]
        showing_date = datetime.strptime(date_raw, "%Y-%m-%d").date() if isinstance(date_raw, str) else date_raw

        key = (film_id, entry["cinema_slug"], showing_date)
        times_raw = entry.get("times", [])
        times_list = times_raw if isinstance(times_raw, list) else [times_raw]

        agg = aggregated.get(key)
        if agg is None:
            agg = {
                "film_id": film_id,
                "cinema_slug": entry["cinema_slug"],
                "date": showing_date,
                "times": [],
                "screens": set(),
                "language": entry.get("language"),
                "buy_url": entry.get("buy_url") or entry.get("source_url"),
            }
            aggregated[key] = agg
        for t in times_list:
            if t and t not in agg["times"]:
                agg["times"].append(t)
        if entry.get("screen"):
            agg["screens"].add(entry["screen"])
        if not agg["language"] and entry.get("language"):
            agg["language"] = entry.get("language")
        if not agg["buy_url"]:
            agg["buy_url"] = entry.get("buy_url") or entry.get("source_url")

    count = 0
    for agg in aggregated.values():
        agg["times"].sort()
        screen = next(iter(agg["screens"])) if len(agg["screens"]) == 1 else None
        showing_repo.upsert(
            db,
            {
                "film_id": agg["film_id"],
                "cinema_slug": agg["cinema_slug"],
                "date": agg["date"],
                "times": json.dumps(agg["times"]),
                "language": agg["language"],
                "screen": screen,
                "buy_url": agg["buy_url"],
            },
        )
        keys_by_cinema.setdefault(agg["cinema_slug"], set()).add((agg["film_id"], agg["date"]))
        count += 1

    if skipped:
        logger.warning("%d showings saltati (film non risolvibile)", skipped)
    return count, keys_by_cinema


def _parse_window(showings_data: dict) -> tuple[date, date]:
    """Finestra coperta dai JSON (`date_from`/`date_to` di showings.json). Fail fast se manca.

    La finestra delimita dove ha senso archiviare: fuori è storia e non si tocca.
    """
    try:
        date_from = date.fromisoformat(showings_data["date_from"])
        date_to = date.fromisoformat(showings_data["date_to"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"showings.json senza finestra valida (date_from/date_to): {exc}") from exc
    if date_to < date_from:
        raise ValueError(f"Finestra invertita in showings.json: da {date_from} a {date_to}")
    return date_from, date_to


def _reconcile_archive(
    db: Session,
    film_keys: set[tuple[str, int | None]],
    showing_keys: dict[str, set[tuple[int, date]]],
    cinema_slugs: list[str],
    date_from: date,
    date_to: date,
    min_ratio: float,
) -> dict[str, int | list[str]]:
    """Archivia i residui e riattiva ciò che ricompare. Mai DELETE.

    Regola (decisione dell'utente, 2026-09-25): i dati non si cancellano mai —
    una riga non più nei JSON dell'ultima importazione è un residuo e si archivia
    con `removed_at`; se ricompare si riattiva e i dati vecchi restano consultabili.

    - film: la regola è l'**assenza** dalle chiavi importate, non la somiglianza
      (alcuni residui hanno chiavi che non assomigliano a nessuna forma attuale);
    - showings: stessa regola, ma solo dentro la finestra coperta dai JSON e per i
      cinema presenti in `cinemas.json`. Fuori finestra non si tocca nulla;
    - guardia anti-fonte-rotta: se per un cinema gli showings importati sono meno di
      `min_ratio` di quelli già nel DB nella finestra, sembra una fonte andata a metà
      e non una programmazione cambiata → l'archiviazione per quel cinema si salta.
    """
    archived_films = film_repo.archive_not_in(db, film_keys)
    reactivated_films = film_repo.reactivate_in(db, film_keys)

    archived_showings = 0
    reactivated_showings = 0
    skipped_cinemas: list[str] = []
    for slug in cinema_slugs:
        keep = showing_keys.get(slug, set())
        existing = showing_repo.count_active_in_window(db, slug, date_from, date_to)
        if existing and len(keep) < min_ratio * existing:
            skipped_cinemas.append(slug)
            logger.warning(
                "Archiviazione saltata per %s: %d showings importati su %d nel DB (ratio minimo %.2f)",
                slug,
                len(keep),
                existing,
                min_ratio,
            )
            continue
        archived_showings += showing_repo.archive_not_in(db, slug, date_from, date_to, keep)
        reactivated_showings += showing_repo.reactivate_in(db, slug, date_from, date_to, keep)

    return {
        "archived_films": archived_films,
        "reactivated_films": reactivated_films,
        "archived_showings": archived_showings,
        "reactivated_showings": reactivated_showings,
        "skipped_cinemas": skipped_cinemas,
    }


def seed_from_json(
    db: Session,
    output_dir: Path,
    *,
    archive_enabled: bool | None = None,
    archive_min_ratio: float | None = None,
) -> dict[str, int | list[str]]:
    """Legge cinemas.json + films.json + showings.json e popola il DB.

    Args:
        db: sessione SQLAlchemy attiva.
        output_dir: cartella con i JSON dello scraper.
        archive_enabled: attiva la riconciliazione con archiviazione. Default:
            `settings.seed_archive_enabled`.
        archive_min_ratio: soglia della guardia anti-fonte-rotta per cinema. Default:
            `settings.seed_archive_min_ratio`.

    Returns:
        dict con i conteggi processati ({"cinemas", "films", "showings"}) più il
        report di archiviazione: {"archived_films", "reactivated_films",
        "archived_showings", "reactivated_showings", "skipped_cinemas"}.
        Un archiviazione silenziosa è un archiviazione che spaventa: i numeri escono
        sempre, anche quando sono zeri.
    """
    settings = get_settings()
    if archive_enabled is None:
        archive_enabled = settings.seed_archive_enabled
    if archive_min_ratio is None:
        archive_min_ratio = settings.seed_archive_min_ratio

    logger.info("Seed da %s", output_dir)

    # Migrazione idempotente: il DB conserva storico e non si ricrea dal seed,
    # quindi le colonne nuove arrivano con un ALTER TABLE (vedi app/maintenance/).
    ensure_removed_at_columns(db.connection())

    cinemas_data = _load_json(output_dir / "cinemas.json")
    films_data = _load_json(output_dir / "films.json")
    showings_data = _load_json(output_dir / "showings.json")

    report: dict[str, int | list[str]] = {
        "archived_films": 0,
        "reactivated_films": 0,
        "archived_showings": 0,
        "reactivated_showings": 0,
        "skipped_cinemas": [],
    }

    try:
        n_cinemas = _seed_cinemas(db, cinemas_data)
        n_films, film_lookup, film_keys = _seed_films(db, films_data)
        n_showings, showing_keys = _seed_showings(db, showings_data, film_lookup)
        if archive_enabled:
            date_from, date_to = _parse_window(showings_data)
            cinema_slugs = [entry["slug"] for entry in cinemas_data.get("cinemas", [])]
            report.update(
                _reconcile_archive(db, film_keys, showing_keys, cinema_slugs, date_from, date_to, archive_min_ratio)
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    logger.info("Seed completato: %d cinema, %d film, %d showings", n_cinemas, n_films, n_showings)
    logger.info(
        "Archiviazione: film %d archiviati / %d riattivati, showings %d archiviati / %d riattivati, "
        "cinema saltati: %s",
        report["archived_films"],
        report["reactivated_films"],
        report["archived_showings"],
        report["reactivated_showings"],
        report["skipped_cinemas"] or "nessuno",
    )

    return {
        "cinemas": n_cinemas,
        "films": n_films,
        "showings": n_showings,
        **report,
    }


def main():
    """Uso standalone: python -m app.seed_from_json"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    settings = get_settings()
    output_dir = Path(settings.scraper_output_dir).resolve()

    # Crea tabelle se non esistono
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        stats = seed_from_json(db, output_dir)
        print(f"OK: {stats}")


if __name__ == "__main__":
    main()
