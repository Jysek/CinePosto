"""Runtime configuration: paths, URLs, API constants, and timezone helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import os
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
HISTORY_DIR = OUTPUT_DIR / "history"
CACHE_DIR = OUTPUT_DIR / "cache"
MOVIES_JSON = OUTPUT_DIR / "movies.json"
ERRORS_JSON = OUTPUT_DIR / "errors.json"
CINEMAS_JSON = OUTPUT_DIR / "cinemas.json"

# Coordinate approssimate - verificare prima del deploy della mappa
#
# maps_place_url: place URL di Google Maps, raccolte a mano il 2026-09-25; servono per
# aprire il luogo salvato (nome, foto, recensioni) invece del pin di coordinate.
# Le URL sono senza i parametri di sessione (hl/entry/g_ep), che scadono e non vanno salvati.
CINEMA_LOCATIONS: dict[str, dict] = {
    "postmodernissimo": {
        "name": "PostModernissimo",
        # Verificato dal sito ufficiale postmodernissimo.com (2026-07-02)
        "address": "Via del Carmine 4, 06121 Perugia PG",
        "city": "Perugia",
        "region": "Umbria",
        "lat": 43.1129,
        "lon": 12.3933,
        "website": "https://www.postmodernissimo.com",
        "maps_place_url": "https://www.google.com/maps/place/PostModernissimo/@43.112795,12.3933012,17z/data=!3m1!4b1!4m6!3m5!1s0x132ea07e158767a5:0xf07683069b4f710c!8m2!3d43.112795!4d12.3933012!16s%2Fg%2F11bbw_zg66",
    },
    "the-space-corciano": {
        "name": "The Space Cinema Corciano",
        # Verificato dal sito ufficiale thespacecinema.it (2026-07-02)
        "address": "Via Pierluigi Nervi, 06073 Corciano PG",
        "city": "Corciano",
        "region": "Umbria",
        "lat": 43.0990,
        "lon": 12.3144,
        "website": "https://www.thespacecinema.it",
        # Nome su Maps "The Space Cinema Crociano-Perugia": refuso del luogo su Maps,
        # confermato dall'utente (2026-09-25) che è la sala giusta.
        "maps_place_url": "https://www.google.com/maps/place/The+Space+Cinema+Crociano-Perugia/@43.099009,12.314361,17z/data=!3m1!4b1!4m6!3m5!1s0x132ea711b9c24fdb:0xe2c0ffd36eaeceec!8m2!3d43.099009!4d12.314361!16s%2Fg%2F11b7ln0zcy",
    },
    "the-space-terni": {
        "name": "The Space Cinema Terni",
        # Verificato dal sito ufficiale thespacecinema.it (2026-09-19)
        "address": "Viale Donato Bramante, Snc, 05100 Terni TR",
        "city": "Terni",
        "region": "Umbria",
        "lat": 42.5727,
        "lon": 12.6355,
        "website": "https://www.thespacecinema.it",
        # Scarto di ~150 m dalle coordinate config: confermato dall'utente (2026-09-25),
        # è la sala giusta e lo scarto è irrilevante.
        "maps_place_url": "https://www.google.com/maps/place/The+Space+Cinema+Terni/@42.571487,12.6365495,17z/data=!3m1!4b1!4m6!3m5!1s0x132efb389b90c005:0x85dc3e8bb721393d!8m2!3d42.571487!4d12.6365495!16s%2Fg%2F1ptw0shwr",
    },
    "uci-perugia": {
        "name": "UCI Cinemas Perugia",
        # Indirizzo indicato da Emanuele (2026-07-02). Verificare su Maps.
        "address": "Viale Centova 1D, 06100 Perugia PG",
        "city": "Perugia",
        "region": "Umbria",
        "lat": 43.0965,
        "lon": 12.3554,
        "website": "https://ucicinemas.it",
        "maps_place_url": "https://www.google.com/maps/place/UCI+Cinemas+Perugia/@43.0964489,12.3554245,17z/data=!3m1!4b1!4m6!3m5!1s0x132ea0b98aff92ed:0x3fb73a068f3414bd!8m2!3d43.0964489!4d12.3554245!16s%2Fg%2F1td2q6pc",
    },
    "cinema-zenith": {
        "name": "Cinema Zenith",
        # Verificato dal JSON-LD del sito ufficiale (2026-09-19)
        "address": "Via Benedetto Bonfigli, 5, 06126 Perugia PG",
        "city": "Perugia",
        "region": "Umbria",
        "lat": 43.10421,
        "lon": 12.39403,
        "website": "https://cinemazenith.it",
        "maps_place_url": "https://www.google.com/maps/place/Cinema+Zenith/@43.1041966,12.3941355,17z/data=!3m1!4b1!4m6!3m5!1s0x132ea0628a88a375:0xc2531e10ebbcd02b!8m2!3d43.1041966!4d12.3941355!16s%2Fg%2F1tj357f8",
    },
    "nuovo-cinema-castello": {
        "name": "Nuovo Cinema Castello",
        # Verificato dal JSON-LD del sito ufficiale (2026-09-19)
        "address": "Piazza Gioberti, 06012 Città di Castello PG",
        "city": "Città di Castello",
        "region": "Umbria",
        "lat": 43.45808,
        "lon": 12.24147,
        "website": "https://www.nuovocinemacastello.it",
        "maps_place_url": "https://www.google.com/maps/place/Nuovo+Cinema+Castello/@43.4581657,12.241471,17z/data=!3m1!4b1!4m6!3m5!1s0x132c7297beb30feb:0x7a7d23f9e1f320e0!8m2!3d43.4581657!4d12.241471!16s%2Fg%2F11bwqqschp",
    },
    "cinema-teatro-concordia": {
        "name": "Cinema Teatro Concordia",
        # Verificato dal microdata del sito ufficiale (2026-09-19)
        "address": "Largo Carlo Goldoni 9, 06055 Marsciano PG",
        "city": "Marsciano",
        "region": "Umbria",
        "lat": 42.90966,
        "lon": 12.33726,
        "website": "https://www.cineconcordia.it",
        "maps_place_url": "https://www.google.com/maps/place/Cinema+Concordia/@42.9097025,12.3372287,17z/data=!3m1!4b1!4m6!3m5!1s0x132ebbf2fc48d631:0x9f1d3182932cd9de!8m2!3d42.9097025!4d12.3372287!16s%2Fg%2F1tdv8y0c",
    },
    "cinema-metropolis": {
        "name": "Cinema Metropolis",
        # Verificato dal microdata del sito ufficiale (2026-09-19)
        "address": "Piazza Carlo Marx, 06019 Umbertide PG",
        "city": "Umbertide",
        "region": "Umbria",
        "lat": 43.30572,
        "lon": 12.33572,
        "website": "https://www.cinemametropolis.it",
        "maps_place_url": "https://www.google.com/maps/place/Cinema+Metropolis/@43.3057053,12.3360185,17z/data=!3m1!4b1!4m6!3m5!1s0x132c10d0688444b9:0x4c165b5f9f294018!8m2!3d43.3057053!4d12.3360185!16s%2Fg%2F1ptxwc63j",
    },
}
SCRAPER_LOG = BASE_DIR / "scraper.log"
WIKIDATA_CACHE = BASE_DIR / ".wikidata_cache.json"

# CinePosto scraper operates in Italian local time. The server may run in UTC,
# so we always compute "today" in Europe/Rome regardless of the host timezone.
# Configurable via the SCRAPER_TZ env var for future deployment in other regions.
SCRAPER_TZ = ZoneInfo(os.environ.get("SCRAPER_TZ", "Europe/Rome"))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

FILMS_JSON = OUTPUT_DIR / "films.json"
SHOWINGS_JSON = OUTPUT_DIR / "showings.json"

CITY = "Perugia"

THE_SPACE_CINEMA_ID = 1027  # venue ID from the TheSpace API (hardcoded for cinema/corciano)
THE_SPACE_CINEMA_NAME = "The Space Cinema Corciano"
THE_SPACE_CINEMA_SLUG = "the-space-corciano"
THE_SPACE_BASE_URL = "https://www.thespacecinema.it"
THE_SPACE_API_BASE = f"{THE_SPACE_BASE_URL}/api/microservice"
THE_SPACE_AUTH_URL = f"{THE_SPACE_API_BASE}/auth/token"
# I venue id non sono stabili: `/showings/cinemas` è l'elenco corrente e i connettori
# risolvono l'id dal nome, con la costante per cinema come fallback (vedi thespace.py).
THE_SPACE_CINEMAS_URL = f"{THE_SPACE_API_BASE}/showings/cinemas"
THE_SPACE_FILMS_URL_TEMPLATE = f"{THE_SPACE_CINEMAS_URL}/{{cinema_id}}/films"
THE_SPACE_FILM_DETAIL_URL = f"{THE_SPACE_BASE_URL}/film/{{film_slug}}"
THE_SPACE_CINEMA_URL = f"{THE_SPACE_BASE_URL}/cinema/corciano/al-cinema"
# Terni: stesso microservizio di Corciano, venue 1006 (verificato 2026-09-19).
THE_SPACE_TERNI_ID = 1006
THE_SPACE_TERNI_NAME = "The Space Cinema Terni"
THE_SPACE_TERNI_SLUG = "the-space-terni"
THE_SPACE_TERNI_URL = f"{THE_SPACE_BASE_URL}/cinema/terni/al-cinema"

UCI_CINEMA_NAME = "UCI Cinemas Perugia"
UCI_CINEMA_SLUG = "uci-perugia"
UCI_BASE_URL = "https://ucicinemas.it"
UCI_CINEMA_URL = f"{UCI_BASE_URL}/cinema/perugia/"
# Undocumented Cloud Run backend — reverse-engineered from XHR traffic. May change on redeployment.
UCI_API_BASE = "https://myuci---uci-backend-production-nfluwp7wga-oc.a.run.app"
UCI_PROGRAMMING_URL = f"{UCI_API_BASE}/api/theatres/uci-cinemas-perugia/programming/{{date}}"

POSTMOD_CINEMA_NAME = "PostModernissimo"
POSTMOD_CINEMA_SLUG = "postmodernissimo"
POSTMOD_BASE_URL = "https://www.postmodernissimo.com"
POSTMOD_CINEMA_URL = POSTMOD_BASE_URL

CINEMA_ZENITH_NAME = "Cinema Zenith"
CINEMA_ZENITH_SLUG = "cinema-zenith"
CINEMA_ZENITH_BASE_URL = "https://cinemazenith.it"
CINEMA_ZENITH_URL = f"{CINEMA_ZENITH_BASE_URL}/"
CINEMA_ZENITH_WEEK_URL = f"{CINEMA_ZENITH_BASE_URL}/programmazione-settimana/"

# Il sito senza `www` risponde 301 verso il proxy Aruba: l'host con `www` è
# obbligatorio in ogni richiesta (vedi docs/scraper/connettori/nuovo-cinema-castello.md).
NUOVO_CASTELLO_NAME = "Nuovo Cinema Castello"
NUOVO_CASTELLO_SLUG = "nuovo-cinema-castello"
NUOVO_CASTELLO_BASE_URL = "https://www.nuovocinemacastello.it"
NUOVO_CASTELLO_URL = f"{NUOVO_CASTELLO_BASE_URL}/"

# `www` obbligatorio: senza risponde 301 verso il proxy Aruba (come Castello).
CONCORDIA_NAME = "Cinema Teatro Concordia"
CONCORDIA_SLUG = "cinema-teatro-concordia"
CONCORDIA_BASE_URL = "https://www.cineconcordia.it"
CONCORDIA_URL = f"{CONCORDIA_BASE_URL}/"

# `www` obbligatorio (come Castello/Concordia). La homepage non ha orari: il
# connettore scopre i film correnti da `/` e poi legge `/films/<slug>/`.
METROPOLIS_NAME = "Cinema Metropolis"
METROPOLIS_SLUG = "cinema-metropolis"
METROPOLIS_BASE_URL = "https://www.cinemametropolis.it"
METROPOLIS_URL = f"{METROPOLIS_BASE_URL}/"
# Alternativa a finestra corta (solo oggi); non usata dal connettore a due fasi.
METROPOLIS_TODAY_URL = f"{METROPOLIS_BASE_URL}/oggi-in-sala/"

REQUEST_TIMEOUT = 30

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
# User-Agent identificabile del progetto (richiesto da AGENTS.md): i nuovi connettori
# lo usano al posto di DEFAULT_USER_AGENT. NON sostituire DEFAULT_USER_AGENT qui:
# i connettori esistenti (postmodernissimo, thespace, uci) si appoggiano a quello Chrome.
PROJECT_USER_AGENT = "CinePosto/1.0 (+https://github.com/Jysek/CinePosto; 55837328+Jysek@users.noreply.github.com)"
REQUEST_RETRY = 3
RETRY_BACKOFF = 2

CLOAKBROWSER_FINGERPRINT_SEED = int(os.environ.get("CLOAKBROWSER_FINGERPRINT_SEED", "42069"))
CLOAKBROWSER_HEADLESS = os.environ.get("CLOAKBROWSER_HEADLESS", "true").lower() == "true"
CLOAKBROWSER_PAGE_TIMEOUT = 30000  # milliseconds (Playwright timeout unit)

SCHEDULE_INTERVAL_HOURS = 24
REMOVAL_THRESHOLD_DAYS = 7  # days without showings → "rimosso"; 2× this value → permanent purge
SCRAPER_RETRY_DELAY = 300  # seconds before retrying a failed connector (5 min — outlasts most CDN TTLs)

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
# Wikimedia policy: identifica un endpoint contattabile reale.
WIKIDATA_USER_AGENT = PROJECT_USER_AGENT
WIKIDATA_TIMEOUT = 15

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = os.environ.get("SCRAPER_LOG_LEVEL", "INFO")


def thespace_films_url(cinema_id: int) -> str:
    """URL delle sessioni di un venue The Space: il cinema è parametrizzato per istanza."""
    return THE_SPACE_FILMS_URL_TEMPLATE.format(cinema_id=cinema_id)


def get_week_dates(ref_date: date | None = None) -> list[str]:
    """Le 8 date ISO da coprire a ogni run: oggi + 7 giorni (finestra di scraping)."""
    d = ref_date or today_local()
    return [(d + timedelta(days=i)).isoformat() for i in range(8)]


def today_local() -> date:
    """Return today's date in the scraper's local timezone.

    Uses `SCRAPER_TZ` (default `Europe/Rome`) so that the scraper rolls over
    to the new "today" at Italian midnight, regardless of the server timezone.
    """
    return datetime.now(SCRAPER_TZ).date()
