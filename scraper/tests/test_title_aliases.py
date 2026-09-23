"""Test della tabella di alias: ogni voce è conoscenza verificata, non indovinata."""

from __future__ import annotations

from scraper.normalizer import title_key
from scraper.title_aliases import TITLE_ALIASES, canonical_title

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
