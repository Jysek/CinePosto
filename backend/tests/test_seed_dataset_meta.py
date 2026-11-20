"""Test della freschezza persistita dal seed (`dataset_meta`).

La data della run arriva da `generated_at` di showings.json, si normalizza in UTC e si
scrive **nella stessa transazione** degli showings. Due corollari sotto test: una run che
non sa dichiarare la propria età non scrive nulla, e un seed non valido non cancella la
data dell'ultima run riuscita. Gli helper della run di test sono quelli di
`test_seed_archive.py`: i JSON hanno lo stesso formato di `scraper/output/`.
"""

from datetime import datetime, timedelta
import json
import time

import pytest
from sqlalchemy import select

from app.models import DatasetMeta, Film, Showing
from app.repositories import dataset_meta_repo, film_repo
from app.seed_from_json import seed_from_json
from tests.test_seed_archive import WINDOW_FROM, _film_entry, _showing_entry, _write_run

# Valore reale emesso dallo scraper: offset +02:00, quindi 11:17:44 UTC.
RUN_GENERATED_AT = "2026-10-03T13:17:44+02:00"
RUN_GENERATED_AT_UTC = datetime(2026, 10, 3, 11, 17, 44)


def _write_run_with(tmp_path, showings, generated_at: str | None = RUN_GENERATED_AT) -> None:
    """Scrive la run di test e impone il `generated_at` del caso (`None` = campo assente)."""
    _write_run(tmp_path, films=[_film_entry("Film")], showings=showings)
    path = tmp_path / "showings.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if generated_at is None:
        payload.pop("generated_at")
    else:
        payload["generated_at"] = generated_at
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_seed_stores_generated_at_as_naive_utc(session, tmp_path):
    """`2026-10-03T13:17:44+02:00` finisce nel DB come UTC naive: 11:17:44, non 13:17:44."""
    _write_run_with(tmp_path, [_showing_entry("Film", WINDOW_FROM)])
    seed_from_json(session, tmp_path)

    assert dataset_meta_repo.get_generated_at(session) == RUN_GENERATED_AT_UTC


def test_second_seed_updates_the_single_row(session, tmp_path):
    """Due seed lasciano una riga sola, con il `generated_at` della run più recente."""
    _write_run_with(
        tmp_path,
        [_showing_entry("Film", WINDOW_FROM)],
        generated_at="2026-10-01T08:00:00+00:00",
    )
    seed_from_json(session, tmp_path)
    first_seeded_at = session.get(DatasetMeta, 1).seeded_at

    # Due seed possono cadere nello stesso tick dell'orologio di Windows (~15 ms).
    time.sleep(0.02)
    _write_run_with(tmp_path, [_showing_entry("Film", WINDOW_FROM + timedelta(days=1))])
    seed_from_json(session, tmp_path)

    rows = session.scalars(select(DatasetMeta)).all()
    assert len(rows) == 1
    assert rows[0].generated_at == RUN_GENERATED_AT_UTC
    # `seeded_at` dice quando e' girato il seed, non quando e' stata creata la riga.
    assert rows[0].seeded_at > first_seeded_at


def test_last_seeded_run_wins_even_if_it_is_older(session, tmp_path):
    """Un JSON piu' vecchio seedato dopo: vince l'ultima seedata, perche' il DB ha quei dati."""
    _write_run_with(tmp_path, [_showing_entry("Film", WINDOW_FROM)])
    seed_from_json(session, tmp_path)

    _write_run_with(
        tmp_path,
        [_showing_entry("Film", WINDOW_FROM)],
        generated_at="2026-10-01T08:00:00+00:00",
    )
    seed_from_json(session, tmp_path)

    assert dataset_meta_repo.get_generated_at(session) == datetime(2026, 10, 1, 8, 0, 0)


def test_failed_seed_rolls_back_meta_and_showings(session, tmp_path, monkeypatch):
    """Errore dopo la scrittura della meta: la transazione si annulla, resta la run precedente.

    E' il tappo vero: senza questo test, il rollback resterebbe una promessa della docstring
    (gli altri casi di errore si fermano prima di qualsiasi scrittura).
    """
    _write_run_with(tmp_path, [_showing_entry("Film", WINDOW_FROM)])
    seed_from_json(session, tmp_path)
    previous_generated_at = dataset_meta_repo.get_generated_at(session)
    showings_before = len(session.scalars(select(Showing)).all())

    def _explode(*args, **kwargs):
        raise RuntimeError("fonte rotta")

    monkeypatch.setattr(film_repo, "archive_not_in", _explode)
    _write_run_with(tmp_path, [_showing_entry("Film", WINDOW_FROM + timedelta(days=1))])

    with pytest.raises(RuntimeError, match="fonte rotta"):
        seed_from_json(session, tmp_path, archive_enabled=True)

    assert dataset_meta_repo.get_generated_at(session) == previous_generated_at
    assert len(session.scalars(select(Showing)).all()) == showings_before


def test_seed_without_generated_at_writes_nothing(session, tmp_path):
    """Showings.json senza `generated_at`: `ValueError` e DB intatto (zero righe, nessuna meta)."""
    _write_run_with(tmp_path, [_showing_entry("Film", WINDOW_FROM)], generated_at=None)

    with pytest.raises(ValueError, match="senza generated_at"):
        seed_from_json(session, tmp_path)

    assert session.scalars(select(Showing)).all() == []
    assert session.scalars(select(Film)).all() == []
    assert dataset_meta_repo.get_generated_at(session) is None


def test_malformed_generated_at_keeps_the_previous_run(session, tmp_path):
    """Secondo seed con `generated_at` malformato: la meta resta quella della prima run."""
    _write_run_with(tmp_path, [_showing_entry("Film", WINDOW_FROM)])
    seed_from_json(session, tmp_path)

    _write_run_with(
        tmp_path,
        [_showing_entry("Film", WINDOW_FROM + timedelta(days=1))],
        generated_at="ieri sera",
    )
    with pytest.raises(ValueError, match="non parsabile"):
        seed_from_json(session, tmp_path)

    assert dataset_meta_repo.get_generated_at(session) == RUN_GENERATED_AT_UTC
    assert len(session.scalars(select(Showing)).all()) == 1  # la run precedente è intatta


def test_generated_at_without_timezone_is_rejected(session, tmp_path):
    """Un `generated_at` senza offset non è utilizzabile: il seed si ferma prima di scrivere."""
    _write_run_with(
        tmp_path,
        [_showing_entry("Film", WINDOW_FROM)],
        generated_at="2026-10-03T13:17:44",
    )

    with pytest.raises(ValueError, match="senza fuso orario"):
        seed_from_json(session, tmp_path)

    assert dataset_meta_repo.get_generated_at(session) is None
