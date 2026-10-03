"""Test end-to-end degli endpoint HTTP.

Testiamo la catena completa router → service → repo → DB in-memory
con TestClient di FastAPI. Ogni test parte da un DB pulito.
"""

from datetime import UTC, date, datetime, timedelta

from app.config import get_settings
from app.models.cinema import Cinema
from app.models.film import Film
from app.models.showing import Showing

# ============ /health ============


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ============ /api/v1/cinema ============


def test_list_cinemas_empty(client):
    """Nessun cinema in DB → lista vuota, non errore."""
    resp = client.get("/api/v1/cinema")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_cinemas_with_data(client, session):
    """Con 2 cinema in DB → ritorna 2 cinema ordinati per nome."""
    session.add_all(
        [
            Cinema(slug="uci", name="UCI", city="Perugia", address="A", region="Umbria", lat=1, lon=1),
            Cinema(slug="pmm", name="PostModernissimo", city="Perugia", address="B", region="Umbria", lat=1, lon=1),
        ]
    )
    session.commit()

    resp = client.get("/api/v1/cinema")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    # Ordine alfabetico
    assert body[0]["name"] == "PostModernissimo"
    assert body[1]["name"] == "UCI"
    # Filtraggio degli attributi: no relazioni, no id interni SQLAlchemy
    assert "showings" not in body[0]


def test_get_cinema_by_slug_returns_with_count(client, sample_cinema):
    resp = client.get(f"/api/v1/cinema/{sample_cinema.slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == sample_cinema.slug
    assert body["showings_count"] == 0  # nessun showing associato


def test_get_cinema_not_found(client):
    """Slug inesistente → 404."""
    resp = client.get("/api/v1/cinema/non-esiste")
    assert resp.status_code == 404
    assert "non trovato" in resp.json()["detail"].lower()


# ============ /api/v1/film ============


def test_films_today_empty(client):
    resp = client.get("/api/v1/film/oggi")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_film_detail_not_found(client):
    resp = client.get("/api/v1/film/9999")
    assert resp.status_code == 404


def test_get_film_detail_returns_detail_schema(client, session, sample_film, sample_cinema):
    """Il dettaglio film include il campo showings (denormalizzato)."""
    session.add(
        Showing(
            film_id=sample_film.id,
            cinema_slug=sample_cinema.slug,
            date=date.today(),
            times='["20:00"]',
        )
    )
    session.commit()

    resp = client.get(f"/api/v1/film/{sample_film.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == sample_film.id
    assert body["title"] == sample_film.title
    assert "synopsis" in body  # campo di FilmDetail
    assert "showings" in body
    assert len(body["showings"]) == 1
    # times deve essere una lista di stringhe (il validator ha parsato la stringa JSON)
    assert body["showings"][0]["times"] == ["20:00"]


# ============ /api/v1/film/search ============


def test_search_requires_min_2_chars(client):
    """Query di 1 carattere → 422 Unprocessable (validazione FastAPI)."""
    resp = client.get("/api/v1/film/search?q=a")
    assert resp.status_code == 422


def test_search_returns_matching_films(client, session):
    """Ricerca case-insensitive con normalizzazione accenti."""
    session.add_all(
        [
            Film(title="Dune", title_normalized="dune", year=2021),
            Film(title="Città Perduta", title_normalized="citta perduta", year=2024),
        ]
    )
    session.commit()

    resp = client.get("/api/v1/film/search?q=citta")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "Città Perduta"


# ============ /api/v1/admin/reimport ============


def test_admin_reimport_requires_token(client):
    """Senza header X-Admin-Token → 422."""
    resp = client.post("/api/v1/admin/reimport")
    assert resp.status_code == 422


def test_admin_reimport_rejects_wrong_token(client):
    resp = client.post(
        "/api/v1/admin/reimport",
        headers={"X-Admin-Token": "token-sbagliato"},
    )
    assert resp.status_code == 403


# ============ /api/v1/dataset ============


# SQLite scrive `scraped_at` come datetime naive in UTC: i test lo simulano
# esplicitamente, per non dipendere dall'orologio del server.
def _naive_utc(hours_ago: int = 0) -> datetime:
    return datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours_ago)


def _add_showing(session, cinema, film, scraped_at: datetime, day_offset: int = 0) -> Showing:
    showing = Showing(
        film_id=film.id,
        cinema_slug=cinema.slug,
        # day_offset diverso per riga: UNIQUE(film_id, cinema_slug, date)
        date=date.today() + timedelta(days=day_offset),
        times='["20:00"]',
        scraped_at=scraped_at,
    )
    session.add(showing)
    session.commit()
    return showing


def test_dataset_info_is_public_and_returns_counts(client, session, sample_cinema, sample_film):
    """GET /dataset senza token → 200 e conteggi coerenti con le righe inserite."""
    _add_showing(session, sample_cinema, sample_film, _naive_utc(), day_offset=0)
    _add_showing(session, sample_cinema, sample_film, _naive_utc(), day_offset=1)

    resp = client.get("/api/v1/dataset")  # nessun header X-Admin-Token
    assert resp.status_code == 200
    body = resp.json()
    assert body["showings"] == 2
    assert body["cinemas"] == 1


def test_dataset_info_is_not_stale_when_scraped_recently(client, session, sample_cinema, sample_film):
    """Dato appena inserito → is_stale False e timestamp in ISO con offset UTC."""
    _add_showing(session, sample_cinema, sample_film, _naive_utc())

    body = client.get("/api/v1/dataset").json()
    assert body["is_stale"] is False
    assert body["age_hours"] < 1
    # Offset esplicito: `new Date(iso)` in JS converte da solo nell'ora locale.
    assert body["latest_scraped_at"].endswith("+00:00")


def test_dataset_info_is_stale_when_older_than_threshold(client, session, sample_cinema, sample_film):
    """Scraping di 48 h fa → oltre la soglia → is_stale True."""
    _add_showing(session, sample_cinema, sample_film, _naive_utc(hours_ago=48))

    body = client.get("/api/v1/dataset").json()
    assert body["is_stale"] is True
    assert body["age_hours"] > body["stale_after_hours"]


def test_dataset_info_is_stale_on_empty_database(client):
    """DB vuoto → stale senza errore: 'nessun dato' è uno stato legittimo, non un 500."""
    resp = client.get("/api/v1/dataset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_stale"] is True
    assert body["latest_scraped_at"] is None
    assert body["age_hours"] is None
    assert body["showings"] == 0
    assert body["cinemas"] == 0


def test_dataset_info_reports_the_configured_threshold(client):
    """La soglia nella risposta è quella di Settings, non un numero cablato nel router."""
    body = client.get("/api/v1/dataset").json()
    assert body["stale_after_hours"] == get_settings().dataset_stale_after_hours
