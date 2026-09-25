"""Test della guardia di identità del seed: un film = una riga.

Regola sotto testo: l'identità di un film si risolve con due segnali, in ordine —
prima la chiave naturale `(title_normalized, year)`, poi il `wikidata_id`. Quando
discordano il seed **non esplode** (`IntegrityError`) e **non duplica**: riusa la
riga del segnale vincente, segnala la coppia e lascia la fusione a
`dedup_films --merge A:B` (decisione umana). Mai DELETE.
"""

from datetime import date
import json

from sqlalchemy import select

from app.models import Film
from app.repositories import film_repo
from app.seed_from_json import seed_from_json

# Finestra fissa dei JSON di test (fuori da oggi: qui si guarda la regola di
# identità, non il calendario reale). Stessa forma di `scraper/output/`.
WINDOW_FROM = date(2026, 9, 25)
WINDOW_TO = date(2026, 10, 2)


def _film_entry(title: str, **extra) -> dict:
    return {"id": title, "title": title, **extra}


def _write_run(tmp_path, films) -> None:
    """Scrive i tre JSON di una run nello stesso formato di `scraper/output/`."""
    (tmp_path / "cinemas.json").write_text(
        json.dumps(
            {
                "cinemas": [
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
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "films.json").write_text(json.dumps({"films": list(films)}), encoding="utf-8")
    (tmp_path / "showings.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-09-25T09:47:22+02:00",
                "date_from": WINDOW_FROM.isoformat(),
                "date_to": WINDOW_TO.isoformat(),
                "showings": [],
            }
        ),
        encoding="utf-8",
    )


def _films(session) -> list[Film]:
    return list(session.scalars(select(Film).order_by(Film.id)))


# ============ Riuso via wikidata_id (N = None, W = riga) ============


def test_upsert_reuses_the_row_found_by_wikidata_when_the_title_changes(session):
    """CASO A: il film torna con un titolo nuovo e lo stesso wikidata → una riga sola, metadati aggiornati."""
    first = film_repo.upsert_from_scraper(
        session,
        {"title": "Cars – 20esimo anniversario", "year": 2006, "wikidata_id": "Q328", "director": "Prima"},
    )
    session.commit()

    reused = film_repo.upsert_from_scraper(
        session,
        {"title": "CARS 20 ANNIVERSARIO", "wikidata_id": "Q328", "director": "Dopo"},
    )
    session.commit()

    films = _films(session)
    assert len(films) == 1  # nessun INSERT, nessun IntegrityError
    assert reused.id == first.id
    assert films[0].director == "Dopo"  # i metadati si aggiornano


def test_upsert_does_not_change_the_natural_key_of_the_reused_row(session):
    """La riga riusata via wikidata conserva title e (title_normalized, year): è la difesa
    contro la forma vecchia che ricompare senza wikidata (se la chiave cambiasse, il lookup
    per chiave non la troverebbe più e ne inserirebbe una seconda)."""
    film_repo.upsert_from_scraper(
        session, {"title": "Cars – 20esimo anniversario", "year": 2006, "wikidata_id": "Q328"}
    )
    session.commit()

    film_repo.upsert_from_scraper(session, {"title": "CARS 20 ANNIVERSARIO", "year": 2007, "wikidata_id": "Q328"})
    session.commit()

    film = _films(session)[0]
    assert film.title == "Cars – 20esimo anniversario"
    assert film.title_normalized == "cars 20esimo anniversario"
    assert film.year == 2006


def test_upsert_reactivates_the_row_reused_by_wikidata(session, tmp_path):
    """La riga archiviata riusata via wikidata torna attiva: `keep_keys` porta la SUA chiave."""
    _write_run(tmp_path, films=[_film_entry("Cars – 20esimo anniversario", year=2006, wikidata_id="Q328")])
    seed_from_json(session, tmp_path)

    _write_run(tmp_path, films=[])  # esce dalla programmazione → archiviata, non cancellata
    seed_from_json(session, tmp_path)

    _write_run(tmp_path, films=[_film_entry("CARS 20 ANNIVERSARIO", wikidata_id="Q328")])
    report = seed_from_json(session, tmp_path)

    films = _films(session)
    assert len(films) == 1  # nessuna riga nuova
    assert films[0].removed_at is None  # riattivata
    assert report["reactivated_films"] == 1


# ============ Conflitto di identità (N = riga, W = riga diversa) ============


def test_upsert_never_writes_a_wikidata_id_already_used_by_another_row(session):
    """CASO B: il wikidata arriva in update su una riga che non lo possiede → nessun crash,
    nessuna delle due righe cambia `wikidata_id`."""
    rosso = film_repo.upsert_from_scraper(session, {"title": "Rosso", "year": 2020})
    session.commit()
    blu = film_repo.upsert_from_scraper(session, {"title": "Blu", "year": 2021, "wikidata_id": "Q1"})
    session.commit()

    result = film_repo.upsert_from_scraper(session, {"title": "Rosso", "year": 2020, "wikidata_id": "Q1"})
    session.commit()

    films = _films(session)
    assert len(films) == 2  # nessun INSERT in conflitto
    assert result.id == rosso.id
    assert films[0].id == rosso.id and films[0].wikidata_id is None  # N non prende il wikidata altrui
    assert films[1].id == blu.id and films[1].wikidata_id == "Q1"  # W resta il proprietario


def test_upsert_prefers_the_natural_key_row_and_reports_the_identity_conflict(session, tmp_path):
    """N ≠ W: si aggiorna N (solo metadati), non si inserisce nulla, la coppia finisce nel report."""
    _write_run(
        tmp_path,
        films=[_film_entry("Rosso", year=2020), _film_entry("Blu", year=2021, wikidata_id="Q1")],
    )
    seed_from_json(session, tmp_path)
    rosso, blu = _films(session)

    _write_run(tmp_path, films=[_film_entry("Rosso", year=2020, director="Nuovo", wikidata_id="Q1")])
    report = seed_from_json(session, tmp_path)

    films = _films(session)
    assert len(films) == 2  # nessun INSERT
    assert report["identity_conflicts"] == [f"{rosso.id}:{blu.id}"]  # formato dedup_films --merge A:B
    assert films[0].id == rosso.id and films[0].director == "Nuovo"  # metadati di N aggiornati
    assert films[0].wikidata_id is None  # nessuna scrittura del wikidata già di W
    assert films[1].id == blu.id and films[1].wikidata_id == "Q1"


# ============ Inserimento e invariante ============


def test_seed_inserts_only_when_both_signals_miss(session, tmp_path):
    """Nessuna chiave naturale e nessun wikidata noto: è l'unico caso in cui si inserisce."""
    _write_run(tmp_path, films=[_film_entry("Nuovo", wikidata_id="Q9", director="Regista")])
    report = seed_from_json(session, tmp_path)

    films = _films(session)
    assert len(films) == 1
    assert films[0].title == "Nuovo"
    assert films[0].wikidata_id == "Q9"
    assert report["identity_conflicts"] == []


def test_seed_flags_active_rows_sharing_the_same_title_with_null_year(session, tmp_path):
    """CASO C: due righe (titolo, NULL) coesistono (NULL ≠ NULL in SQL) → segnalate, mai fuse."""
    session.add_all([Film(title="Dune", title_normalized="dune"), Film(title="Dune", title_normalized="dune")])
    session.commit()
    first_id, second_id = (film.id for film in _films(session))

    _write_run(tmp_path, films=[_film_entry("Dune")])
    report = seed_from_json(session, tmp_path)

    assert report["duplicate_titles"] == [f"{first_id}:{second_id}"]
    assert report["identity_conflicts"] == []
    assert len(_films(session)) == 2  # nessuna fusione automatica: possono essere remake con anno ignoto


def test_second_seed_with_the_guard_changes_nothing(session, tmp_path):
    """Due run identiche su dati puliti: la seconda non cambia nulla e la guardia è silenziosa."""
    _write_run(tmp_path, films=[_film_entry("Uno", year=2024, wikidata_id="Q1"), _film_entry("Due", year=2025)])
    seed_from_json(session, tmp_path)

    report = seed_from_json(session, tmp_path)

    assert report["archived_films"] == 0
    assert report["reactivated_films"] == 0
    assert report["identity_conflicts"] == []
    assert report["duplicate_titles"] == []
    assert len(_films(session)) == 2
