"""Test del campo maps_place_url: ogni cinema di CINEMA_LOCATIONS porta la place
URL di Google Maps e finisce — senza modifiche ai serializer — in cinemas.json e
nella validazione dell'output.

Il campo è nato per aprire dall'app la scheda del **luogo salvato** su Maps (nome,
foto, recensioni) invece del pin di coordinate. Le URL sono state raccolte a mano
il 2026-09-25 e sono confermate dall'utente (i due The Space e Cinema Concordia).
"""

import json
from pathlib import Path
import sys

from scraper.config import CINEMA_LOCATIONS
from scraper.models import cinemas_to_json
from validate_output import ERRORS, WARNINGS, validate_cinemas

# La validazione gira su un cinemas.json reale in output/: la si punta a una
# fixture temporanea per non dipendere dal file committato.
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
CINEMAS_JSON = OUTPUT_DIR / "cinemas.json"


def test_cinemas_to_json_includes_maps_place_url_for_every_cinema():
    """Tutti e 8 i cinema hanno una place URL che finisce intatta in cinemas.json.

    `cinemas_to_json` fa `{"slug": slug, **data}`: ogni chiave nuova in
    CINEMA_LOCATIONS si propaga da sola — il test lo garantisce, così nessuna
    evoluzione di contratto resta indietro per un filtro dimenticato.
    """
    result = cinemas_to_json(CINEMA_LOCATIONS)

    cinema_entries = result["cinemas"]
    slugs = [c["slug"] for c in cinema_entries]
    assert len(cinema_entries) == 8
    assert set(slugs) == set(CINEMA_LOCATIONS)

    for entry in cinema_entries:
        expected = CINEMA_LOCATIONS[entry["slug"]]["maps_place_url"]
        assert entry["maps_place_url"] == expected
        assert entry["maps_place_url"].startswith("https://www.google.com/maps/place/")


def test_validate_output_passes_on_the_committed_cinemas_without_warnings():
    """Il cinemas.json committato è valido: nessun errore e nessun warning
    (in particolare: nessuna maps_place_url mancante o malformata)."""
    WARNINGS.clear()
    ERRORS.clear()
    validate_cinemas()

    url_warnings = [w for w in WARNINGS if "maps_place_url" in w]
    assert url_warnings == []
    assert ERRORS == []


def test_validate_output_warns_when_maps_place_url_missing(tmp_path):
    """Un cinema senza maps_place_url è un warning, non un errore: il campo è
    opzionale (un cinema senza URL non è un dato rotto) ma la mancanza si segnala."""
    data = {
        "cinemas": [
            {
                "slug": "test-sala",
                "name": "Sala Test",
                "lat": 43.0,
                "lon": 12.0,
                "website": "https://example.com",
            }
        ]
    }
    fake = tmp_path / "cinemas.json"
    fake.write_text(json.dumps(data), encoding="utf-8")

    real = sys.modules["validate_output"].CINEMAS_JSON
    sys.modules["validate_output"].CINEMAS_JSON = fake
    try:
        WARNINGS.clear()
        ERRORS.clear()
        validate_cinemas()

        assert any("maps_place_url mancante" in w for w in WARNINGS)
        assert ERRORS == []
    finally:
        sys.modules["validate_output"].CINEMAS_JSON = real


def test_validate_output_errors_when_maps_place_url_is_malformed(tmp_path):
    """Una URL di altra forma (per esempio una ricerca per coordinate) invierebbe
    l'utente al pin senza scheda del luogo: è un errore critico, non un stile."""
    data = {
        "cinemas": [
            {
                "slug": "sala-rotta",
                "name": "Sala Rotta",
                "lat": 43.0,
                "lon": 12.0,
                "website": "https://example.com",
                "maps_place_url": "https://www.google.com/maps/search/?api=1&query=43.0,12.0",
            }
        ]
    }
    fake = tmp_path / "cinemas.json"
    fake.write_text(json.dumps(data), encoding="utf-8")

    real = sys.modules["validate_output"].CINEMAS_JSON
    sys.modules["validate_output"].CINEMAS_JSON = fake
    try:
        WARNINGS.clear()
        ERRORS.clear()
        validate_cinemas()

        assert any("maps_place_url malformata" in e for e in ERRORS)
    finally:
        sys.modules["validate_output"].CINEMAS_JSON = real
