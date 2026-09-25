"""Test dell'archiviazione dei residui del seed (soft delete con `removed_at`).

Regola sotto testo: i dati **non si cancellano mai**. Le righe non più nei JSON
dell'ultima importazione si archiviano (`removed_at` valorizzato); se ricompaiono
si riattivano. I JSON di ogni run si scrivono in una cartella tmp nello stesso
formato di `scraper/output/`, così il test gira sul vero `seed_from_json`.
"""

from datetime import date, datetime, timedelta
import json

from sqlalchemy import select

from app.models import Film, Showing
from app.seed_from_json import seed_from_json

# Finestra fissa usata dai JSON di test (fuori da oggi: questi test non guardano
# il calendario reale, guardano la regola di archiviazione).
WINDOW_FROM = date(2026, 9, 25)
WINDOW_TO = date(2026, 10, 2)


def _film_entry(title: str, **extra) -> dict:
    return {"id": title, "title": title, **extra}


def _showing_entry(film_title: str, day: date, cinema_slug: str = "c1", times=("20:00",)) -> dict:
    return {"film_id": film_title, "cinema_slug": cinema_slug, "date": day.isoformat(), "times": list(times)}


def _write_run(tmp_path, films, showings, cinemas=None) -> None:
    """Scrive i tre JSON di una run nello stesso formato di scraper/output/."""
    if cinemas is None:
        cinemas = [
            {
                "slug": "c1",
                "name": "Cinema Uno",
                "city": "Perugia",
                "address": "Via Roma 1",
                "region": "Umbria",
                "lat": 43.11,
                "lon": 12.39,
            }
        ]
    (tmp_path / "cinemas.json").write_text(json.dumps({"cinemas": cinemas}), encoding="utf-8")
    (tmp_path / "films.json").write_text(json.dumps({"films": list(films)}), encoding="utf-8")
    (tmp_path / "showings.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-09-25T09:47:22+02:00",
                "date_from": WINDOW_FROM.isoformat(),
                "date_to": WINDOW_TO.isoformat(),
                "showings": list(showings),
            }
        ),
        encoding="utf-8",
    )


def _films_by_title(session) -> dict[str, Film]:
    return {f.title: f for f in session.scalars(select(Film))}


# ============ Film ============


def test_seed_archives_film_absent_from_json(session, tmp_path):
    """Un film nel DB che non è più nei JSON si archiva, ma la riga resta (nessuna DELETE)."""
    _write_run(tmp_path, films=[_film_entry("Nuovo"), _film_entry("Vecchio")], showings=[])
    seed_from_json(session, tmp_path)

    _write_run(tmp_path, films=[_film_entry("Nuovo")], showings=[])
    report = seed_from_json(session, tmp_path)

    assert report["archived_films"] == 1
    films = _films_by_title(session)
    assert set(films) == {"Nuovo", "Vecchio"}  # la riga archiviata è ancora lì
    assert films["Vecchio"].removed_at is not None
    assert films["Nuovo"].removed_at is None


def test_seed_reactivates_film_when_it_returns(session, tmp_path):
    """La stessa chiave naturale che ricompare nei JSON riattiva la riga e aggiorna i campi."""
    _write_run(tmp_path, films=[_film_entry("Ritorna", director="Prima")], showings=[])
    seed_from_json(session, tmp_path)

    _write_run(tmp_path, films=[], showings=[])
    seed_from_json(session, tmp_path)

    _write_run(tmp_path, films=[_film_entry("Ritorna", director="Dopo")], showings=[])
    report = seed_from_json(session, tmp_path)

    assert report["reactivated_films"] == 1
    films = _films_by_title(session)
    assert len(films) == 1  # nessuna riga nuova: è la stessa, riattivata
    assert films["Ritorna"].removed_at is None
    assert films["Ritorna"].director == "Dopo"


# ============ Showings ============


def test_seed_archives_showings_absent_from_json_within_window(session, tmp_path):
    """Gli showings assenti dai JSON si archiviano dentro la finestra, quelli fuori restano storia."""
    day_in_window = WINDOW_FROM + timedelta(days=1)
    _write_run(
        tmp_path,
        films=[_film_entry("A"), _film_entry("B")],
        showings=[_showing_entry("A", day_in_window), _showing_entry("B", WINDOW_TO)],
    )
    seed_from_json(session, tmp_path)

    # Storia: uno showing di una run precedente, fuori dalla finestra dei JSON.
    film_a = _films_by_title(session)["A"]
    history_day = WINDOW_FROM - timedelta(days=10)
    session.add(Showing(film_id=film_a.id, cinema_slug="c1", date=history_day, times='["18:00"]'))
    session.commit()

    _write_run(
        tmp_path,
        films=[_film_entry("A"), _film_entry("B")],
        showings=[_showing_entry("A", day_in_window)],
    )
    report = seed_from_json(session, tmp_path)

    assert report["archived_showings"] == 1  # solo B dentro la finestra
    showings = {(s.film_id, s.date): s for s in session.scalars(select(Showing))}
    assert showings[(film_a.id, day_in_window)].removed_at is None  # importato: resta
    assert showings[(film_a.id, history_day)].removed_at is None  # fuori finestra: non toccato


def test_seed_skips_cinema_when_import_ratio_is_below_threshold(session, tmp_path):
    """Una fonte andata a metà non archivia nulla per quel cinema: lo dice `skipped_cinemas`."""
    day_one = WINDOW_FROM + timedelta(days=1)
    day_two = WINDOW_FROM + timedelta(days=2)
    _write_run(
        tmp_path,
        films=[_film_entry("A"), _film_entry("B")],
        showings=[
            _showing_entry("A", day_one),
            _showing_entry("B", day_two),
            _showing_entry("A", day_two),
            _showing_entry("B", day_one),
        ],
    )
    seed_from_json(session, tmp_path)

    # Run "rotta": 1 showing importato su 4 già nel DB → sotto la soglia 0.5.
    _write_run(
        tmp_path,
        films=[_film_entry("A"), _film_entry("B")],
        showings=[_showing_entry("A", day_one)],
    )
    report = seed_from_json(session, tmp_path)

    assert report["skipped_cinemas"] == ["c1"]
    assert report["archived_showings"] == 0
    stale = {(s.film_id, s.date): s for s in session.scalars(select(Showing))}
    assert all(s.removed_at is None for s in stale.values())  # nessuno archiviato


def test_second_seed_of_the_same_data_changes_nothing(session, tmp_path):
    """Rieseguire il seed sugli stessi JSON non cambia nulla: tutti i contatori a 0."""
    day_in_window = WINDOW_FROM + timedelta(days=1)
    run = dict(
        films=[_film_entry("Solo"), _film_entry("Residuo")],
        showings=[_showing_entry("Solo", day_in_window)],
    )
    _write_run(tmp_path, **run)
    seed_from_json(session, tmp_path)

    # Una run senza "Residuo" lo archivia (prima volta: i contatori non sono a zero)...
    _write_run(tmp_path, films=[_film_entry("Solo")], showings=[_showing_entry("Solo", day_in_window)])
    first = seed_from_json(session, tmp_path)
    assert first["archived_films"] == 1

    # ...la stessa run ripetuta è un no-op.
    _write_run(tmp_path, films=[_film_entry("Solo")], showings=[_showing_entry("Solo", day_in_window)])
    report = seed_from_json(session, tmp_path)

    assert report == {
        "cinemas": 1,
        "films": 1,
        "showings": 1,
        "archived_films": 0,
        "reactivated_films": 0,
        "archived_showings": 0,
        "reactivated_showings": 0,
        "skipped_cinemas": [],
        "identity_conflicts": [],
        "duplicate_titles": [],
    }


# ============ Query pubbliche ============


def test_today_and_week_queries_hide_archived_films(client, session, sample_cinema):
    """Un film archiviato non compare in /film/oggi nemmeno con showings in finestra."""
    today = date.today()
    active = Film(title="Attivo", title_normalized="attivo", year=2026)
    archived = Film(title="Archiviato", title_normalized="archiviato", year=2026, removed_at=datetime.now())
    session.add_all([active, archived])
    session.flush()
    session.add_all(
        [
            Showing(film_id=active.id, cinema_slug=sample_cinema.slug, date=today, times='["20:00"]'),
            Showing(film_id=archived.id, cinema_slug=sample_cinema.slug, date=today, times='["21:00"]'),
        ]
    )
    session.commit()

    today_titles = [film["title"] for film in client.get("/api/v1/film/oggi").json()]
    week_titles = [film["title"] for film in client.get("/api/v1/film/settimana").json()]

    assert today_titles == ["Attivo"]
    assert week_titles == ["Attivo"]


def test_search_hides_archived_films(client, session):
    """La ricerca per titolo non riporta i film archiviati."""
    session.add_all(
        [
            Film(title="Città Magica", title_normalized="citta magica", year=2026),
            Film(title="Città Perduta", title_normalized="citta perduta", year=2025, removed_at=datetime.now()),
        ]
    )
    session.commit()

    results = client.get("/api/v1/film/search?q=citta").json()

    assert [film["title"] for film in results] == ["Città Magica"]


def test_api_response_shape_is_unchanged(client, session, sample_cinema, sample_film):
    """`removed_at` è un fatto interno del DB: non compare in nessuna risposta pubblica."""
    today = date.today()
    session.add(Showing(film_id=sample_film.id, cinema_slug=sample_cinema.slug, date=today, times='["20:00"]'))
    session.commit()

    endpoints = [
        "/api/v1/film/oggi",
        f"/api/v1/film/{sample_film.id}",
        f"/api/v1/showings?date={today.isoformat()}",
        f"/api/v1/cinema/{sample_cinema.slug}/showings",
    ]
    for endpoint in endpoints:
        body = client.get(endpoint).json()
        payloads = body if isinstance(body, list) else [body]
        for payload in payloads:
            assert "removed_at" not in payload
            for nested in ("film", "cinema", "showings"):
                items = payload.get(nested, [])
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    assert "removed_at" not in item
