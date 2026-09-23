"""Fusione per identità Wikidata, scelta del titolo del master, pipeline di dedup.

Nessuna rete: i `Film` sono costruiti a mano, come se l'arricchimento li avesse
già identificati (o no).
"""

from __future__ import annotations

from scraper.main import (
    _choose_master_title,
    _deduplicate_films,
    _merge_films_by_wikidata_id,
)
from scraper.models import Film, Showing
from scraper.normalizer import normalize_title


def make_film(
    title: str,
    wikidata_id: str | None = None,
    *,
    cinema: str = "X",
    director: str | None = None,
    year: int | None = None,
) -> Film:
    return Film(
        title=title,
        title_normalized=normalize_title(title),
        wikidata_id=wikidata_id,
        director=director,
        year=year,
        present_in=[Showing(cinema=cinema, cinema_slug=cinema.lower(), date="2026-09-23", times=["21:00"])],
    )


def test_merges_films_with_the_same_wikidata_id():
    # due titoli che nessuna regola di stringa unirebbe, ma stessa identità
    godfather = make_film("Il padrino", "Q47845", cinema="A", director="Francis Ford Coppola")
    the_godfather = make_film("The Godfather", "Q47845", cinema="B", year=1972)

    merged = _merge_films_by_wikidata_id([godfather, the_godfather])

    assert len(merged) == 1
    assert sorted(s.cinema_slug for s in merged[0].present_in) == ["a", "b"]
    # i metadati mancanti arrivano dal gruppo, lo storico si accumula
    assert merged[0].director == "Francis Ford Coppola"
    assert merged[0].year == 1972
    # l'input non viene modificato
    assert len(godfather.present_in) == 1
    assert len(the_godfather.present_in) == 1


def test_does_not_merge_films_with_different_wikidata_ids():
    films = [make_film("Il padrino", "Q47845"), make_film("Barbie", "Q108188280")]

    assert len(_merge_films_by_wikidata_id(films)) == 2


def test_leaves_films_without_wikidata_id_untouched():
    # stesso titolo addirittura, ma senza identità non si fonde nulla
    films = [make_film("Il ritorno del Jedi"), make_film("Il ritorno del Jedi")]

    assert len(_merge_films_by_wikidata_id(films)) == 2


def test_merge_by_wikidata_is_idempotent():
    films = [
        make_film("Il padrino", "Q47845", cinema="A"),
        make_film("The Godfather", "Q47845", cinema="B"),
    ]

    once = _merge_films_by_wikidata_id(films)
    twice = _merge_films_by_wikidata_id(once)

    assert len(once) == 1
    assert [f.title for f in twice] == [f.title for f in once]
    assert len(twice[0].present_in) == 2


def test_master_title_prefers_the_form_that_is_not_shouted():
    assert _choose_master_title(["AMORI & INCANTESIMI 2", "Amori e incantesimi 2"]) == "Amori e incantesimi 2"
    # se sono tutti urlati resta il primo incontrato
    assert _choose_master_title(["AMORI & INCANTESIMI 2", "ANCORA URLATO"]) == "AMORI & INCANTESIMI 2"
    # per un alias noto vince il titolo canonico, in qualunque ordine arrivino
    shouting = "CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO"
    canonical = "Cars – 20esimo anniversario"
    assert _choose_master_title([shouting, canonical]) == canonical
    assert _choose_master_title([canonical, shouting]) == canonical


def test_deduplicated_output_has_no_duplicate_wikidata_id():
    # lista mista: un doppione per Wikidata, uno per alias, un sequel da NON fondere
    films = [
        make_film("Il padrino", "Q47845", cinema="A"),
        make_film("The Godfather", "Q47845", cinema="B"),
        make_film("Barbie", "Q108188280", cinema="A"),
        make_film("CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO", cinema="A"),
        make_film("Cars – 20esimo anniversario", cinema="B"),
        make_film("Amori e incantesimi 2", cinema="A"),
        make_film("Amori e incantesimi", cinema="B"),
    ]

    result = _merge_films_by_wikidata_id(_deduplicate_films(films))

    # un solo film per identità: né doppioni per Wikidata né per alias
    wikidata_ids = [f.wikidata_id for f in result if f.wikidata_id]
    assert len(wikidata_ids) == len(set(wikidata_ids))
    cars = [f for f in result if "cars" in f.title_normalized.lower()]
    assert len(cars) == 1
    assert cars[0].title == "Cars – 20esimo anniversario"
    # ...mentre il sequel resta un film suo, con il «2» nell'id
    assert sorted(f.title_normalized for f in result if "ncantesimi" in f.title_normalized) == [
        "Amori e incantesimi",
        "Amori e incantesimi 2",
    ]
    assert len(result) == 5
