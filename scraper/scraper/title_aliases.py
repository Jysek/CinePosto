"""Alias di titoli fra fonti diverse: la conoscenza che le stringhe non hanno.

Ogni voce è una coppia (variante, titolo canonico) di titoli che le sale
pubblicano in modo diverso ma che indicano lo stesso film. Non si indovina: si
verifica a mano (una volta) e si annota con la fonte e la data. Le chiavi sono
confrontate con `title_key`, quindi non contano maiuscole, punteggiatura,
accenti o suffissi di sala.

Regole della tabella (non degradarle):

- un alias si aggiunge SOLO con la verifica delle due fonti e la data nel
  commento: questa è manutenzione manuale, ed è il prezzo di fondere film che
  le fonti chiamano diversamente — più onesto di una soglia di somiglianza che,
  allentata abbastanza, unirebbe anche film diversi;
- mai un alias "probabile": se è probabile, non si aggiunge (meglio due schede
  che un film sbagliato);
- il titolo canonico è quello che si vuole mostrare all'utente (tipicamente la
  forma corretta, non quella urlata in maiuscolo);
- ogni voce ha il proprio caso in `tests/test_title_aliases.py`:
  `test_every_alias_entry_is_covered_by_a_test` fa rispettare la regola.

Se un caso si ripete (l'arricchimento Wikidata non trova l'entità per titoli
"urlati" o con sottotitoli italiani), la strada giusta è migliorare
`enrich_film`, non allungare questa lista.
"""

from __future__ import annotations

from scraper.normalizer import title_key

# The Space (Corciano/Terni) e UCI (Perugia) annunciano la riedizione del 20°
# anniversario di *Cars* come "CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO",
# Metropolis (Perugia) come "Cars – 20esimo anniversario". Stesso film: verificato
# il 2026-09-22 sui rispettivi siti (nessuna delle due forme trova l'entità
# Wikidata, quindi l'identità non arriva dall'arricchimento).
TITLE_ALIASES: list[tuple[str, str]] = [
    ("CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO", "Cars – 20esimo anniversario"),
]


def canonical_title(title: str) -> str:
    """Ritorna il titolo canonico per un alias noto, altrimenti il titolo stesso."""
    key = title_key(title)
    for variant, canonical in TITLE_ALIASES:
        if key in (title_key(variant), title_key(canonical)):
            return canonical
    return title
