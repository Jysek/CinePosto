"""Test del campo `maps_place_url` lungo tutta la catena backend: migrazione,
seed dai JSON e esposizione via API.

Il campo è nullable per design: un cinema senza place URL di Google Maps non è
un errore, l'app cade indietro alla URL a coordinate.
"""

import json

from sqlalchemy import create_engine, select

from app.maintenance.migrate_maps_place_url import ensure_maps_place_url_column_on_engine
from app.models import Cinema
from app.seed_from_json import seed_from_json

# Place URL del Cinema Concordia: è l'esempio fornito dall'utente il 2026-09-25.
CONCORDIA_URL = (
    "https://www.google.com/maps/place/Cinema+Concordia/"
    "@42.9097025,12.3372287,17z/data=!4m6!3m5!1s0x132ebbf2fc48d631:0x9f1d3182932cd9de"
    "!8m2!3d42.9097025!4d12.3372287!16s%2Fg%2F1tdv8y0c"
)


def _write_cinemas_json(tmp_path, entries) -> None:
    (tmp_path / "cinemas.json").write_text(json.dumps({"cinemas": entries}), encoding="utf-8")
    (tmp_path / "films.json").write_text(json.dumps({"films": []}), encoding="utf-8")
    (tmp_path / "showings.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-09-25T09:47:22+02:00",
                "date_from": "2026-09-25",
                "date_to": "2026-10-02",
                "showings": [],
            }
        ),
        encoding="utf-8",
    )


def _cinema_entry(slug: str, **extra) -> dict:
    base = {
        "slug": slug,
        "name": f"Cinema {slug}",
        "city": "Perugia",
        "address": "Via Test 1",
        "region": "Umbria",
        "lat": 43.11,
        "lon": 12.39,
    }
    base.update(extra)
    return base


# ============ Migrazione ============


def test_migration_adds_maps_place_url_column_to_legacy_cinemas():
    """Un DB creato prima del campo riceve la colonna con un ALTER TABLE."""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE cinemas (slug VARCHAR PRIMARY KEY, name VARCHAR, lat FLOAT, lon FLOAT)")

    applied = ensure_maps_place_url_column_on_engine(engine)

    assert applied is True
    with engine.begin() as conn:
        columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(cinemas)").fetchall()}
        assert "maps_place_url" in columns


def test_migration_is_idempotent_on_a_modern_schema(engine):
    """Su uno schema già aggiornato (create_all col modello nuovo) non fa nulla."""
    assert not ensure_maps_place_url_column_on_engine(engine)


# ============ Seed ============


def test_seed_persists_maps_place_url_from_json(session, tmp_path):
    """La place URL nel cinemas.json arriva fino alla riga del DB, intatta."""
    _write_cinemas_json(
        tmp_path,
        [
            _cinema_entry("cinema-teatro-concordia", maps_place_url=CONCORDIA_URL),
            _cinema_entry("sala-senza-url"),
        ],
    )

    seed_from_json(session, tmp_path)

    concordia = session.scalar(select(Cinema).where(Cinema.slug == "cinema-teatro-concordia"))
    assert concordia.maps_place_url == CONCORDIA_URL


def test_seed_leaves_maps_place_url_null_when_the_field_is_missing(session, tmp_path):
    """Un cinema senza il campo nel JSON si salva con maps_place_url=NULL:
    niente default inventati — la mancanza resta visibile, l'app testerà il campo."""
    _write_cinemas_json(tmp_path, [_cinema_entry("sala-senza-url")])

    seed_from_json(session, tmp_path)

    cinema = session.scalar(select(Cinema).where(Cinema.slug == "sala-senza-url"))
    assert cinema.maps_place_url is None


def test_seed_updates_maps_place_url_on_reimport(session, tmp_path):
    """Al re-seed la place URL si aggiorna (l'upsert aggiorna i campi, non solo l'insert)."""
    _write_cinemas_json(tmp_path, [_cinema_entry("sala-x")])
    seed_from_json(session, tmp_path)

    nuova = "https://www.google.com/maps/place/Cinema+X/@43.1,12.3,17z"
    _write_cinemas_json(tmp_path, [_cinema_entry("sala-x", maps_place_url=nuova)])
    seed_from_json(session, tmp_path)

    cinema = session.scalar(select(Cinema).where(Cinema.slug == "sala-x"))
    assert cinema.maps_place_url == nuova


# ============ API ============


def test_cinema_api_returns_maps_place_url(client, session):
    """L'endpoint /api/v1/cinema espone il campo quando c'è."""
    session.add(
        Cinema(
            slug="cinema-teatro-concordia",
            name="Cinema Teatro Concordia",
            city="Marsciano",
            address="Largo Carlo Goldoni 9",
            region="Umbria",
            lat=42.90966,
            lon=12.33726,
            maps_place_url=CONCORDIA_URL,
        )
    )
    session.commit()

    resp = client.get("/api/v1/cinema")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["maps_place_url"] == CONCORDIA_URL


def test_cinema_api_returns_null_maps_place_url_when_missing(client, session):
    """Un cinema senza URL non rompe nulla: il campo è null, non assente né errore."""
    session.add(
        Cinema(
            slug="sala-senza-url",
            name="Sala Senza URL",
            city="Perugia",
            address="Via Test 1",
            region="Umbria",
            lat=43.11,
            lon=12.39,
        )
    )
    session.commit()

    resp = client.get("/api/v1/cinema")
    assert resp.status_code == 200
    assert resp.json()[0]["maps_place_url"] is None
