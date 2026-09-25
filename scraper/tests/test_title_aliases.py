"""Test della tabella di alias e del match cross-fonte: ogni voce è conoscenza
verificata, non indovinata; il match cross-fonte fonde le varianti dello stesso
film e non fonde mai film diversi."""

from __future__ import annotations

from itertools import permutations

import pytest

from scraper.main import _deduplicate_films
from scraper.models import Film, Showing
from scraper.normalizer import normalize_title, title_key
from scraper.title_aliases import TITLE_ALIASES, canonical_title, match_cross_source

# Coppie (variante, canonico) attese: una per voce di TITLE_ALIASES.
# Chi aggiunge un alias aggiunge qui il proprio caso: la regola del docstring
# di `title_aliases.py` la fa rispettare
# `test_every_alias_entry_is_covered_by_a_test`.
ALIAS_CASES = [
    ("CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO", "Cars – 20esimo anniversario"),
]


def test_known_alias_maps_to_the_canonical_title():
    for variant, canonical in ALIAS_CASES:
        assert canonical_title(variant) == canonical
    # il titolo canonico è un punto fisso: ricevere già il canonico lo riammette
    for _variant, canonical in ALIAS_CASES:
        assert canonical_title(canonical) == canonical


def test_unknown_title_is_returned_unchanged():
    assert canonical_title("Oppenheimer") == "Oppenheimer"


def test_alias_is_case_and_punctuation_insensitive():
    # la stessa voce scritta con maiuscole diverse e trattino ASCII
    assert canonical_title("Cars - Motori Ruggenti - 20mo Anniversario") == "Cars – 20esimo anniversario"


def test_every_alias_entry_is_covered_by_a_test():
    assert len(TITLE_ALIASES) == len(ALIAS_CASES)
    assert {title_key(v) for v, _ in TITLE_ALIASES} == {title_key(v) for v, _ in ALIAS_CASES}


# --- match_cross_source: le tre varianti di *Cars* (fase-15) ---
# The Space annuncia la riedizione del 20° anniversario con la forma lunga,
# Metropolis con «Cars – 20esimo anniversario», UCI e Nuovo Cinema Castello
# con la forma breve: stesso film, tre scritture.
CARS_SPACE = "CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO"
CARS_METROPOLIS = "Cars – 20esimo anniversario"
CARS_SHORT = "Cars - Motori Ruggenti"


def _make_film(title: str, cinema: str) -> Film:
    return Film(
        title=title,
        title_normalized=normalize_title(title),
        present_in=[Showing(cinema=cinema, cinema_slug=cinema.lower(), date="2026-09-25", times=["21:00"])],
    )


def test_fonde_la_variante_breve_con_la_forma_estesa_che_la_contiene():
    # nessun alias fra queste due: le unisce il contenimento sulle forme GREZZE
    assert match_cross_source(CARS_SHORT, CARS_SPACE)


def test_fonde_le_due_forme_note_dall_alias_anche_se_non_si_somigliano():
    # «cars20esimoanniversario» e «carsmotoriruggenti20moanniversario» non hanno
    # contenimento né distanza breve: le unisce solo l'alias curato
    assert match_cross_source(CARS_METROPOLIS, CARS_SPACE)


@pytest.mark.parametrize("titles", list(permutations([CARS_SPACE, CARS_METROPOLIS, CARS_SHORT])))
def test_una_sola_scheda_per_le_tre_varianti_di_cars(titles):
    # qualunque sia l'ordine in cui arrivano i cinema: una scheda sola, con gli
    # showings di tutti (prima dipendeva dall'ordine dei connettori)
    films = [_make_film(title, cinema=f"sala-{i}") for i, title in enumerate(titles)]

    fused = _deduplicate_films(films)

    assert len(fused) == 1
    assert sorted(s.cinema_slug for s in fused[0].present_in) == ["sala-0", "sala-1", "sala-2"]


def test_non_fonde_due_film_diversi():
    assert not match_cross_source("Oppenheimer", "Barbie")
    assert not match_cross_source("Il padrino", "La vita è bella")


def test_non_fonde_un_sequel_numerato_col_primo_film():
    # regressione della guardia sulle cifre finali, vista dal match cross-fonte
    assert not match_cross_source("Amori e incantesimi 2", "Amori e incantesimi")


@pytest.mark.xfail(
    strict=True,
    reason="problema aperto: il contenimento fonde i sequel con numeri romani "
    "(docs/problemi-aperti.md «Un sequel con numero romano può essere fuso con il primo film»). "
    "Quando si risolve lì, questo test diventa passante e la voce si cancella dal registro.",
)
def test_non_fonde_sequel_con_numeri_romani():
    # oggi «Rocky II» contiene «Rocky» e il contenimento le unisce: la guardia
    # copre solo le cifre arabe, non i numeri romani
    assert not match_cross_source("Rocky II", "Rocky")
