"""Estrattore condiviso schema.org per i connettori cinema (JSON-LD + microdata).

Una sola logica di parsing per le tre forme di markup osservate sui siti Umbria:

1. **JSON-LD `@graph`** nel `<head>` (Zenith, Nuovo Cinema Castello) — i `Movie`
   sono riferiti da `ScreeningEvent.workPresented.@id`;
2. **microdata** con `[itemprop=startDate][content]` (Concordia, Metropolis) — il
   `Movie` è annidato dentro lo `ScreeningEvent`;
3. **microdata** con `<time datetime itemprop=startDate>` (pagina
   `programmazione-settimana` di Zenith) — il titolo è la stringa di
   `workPresented` (`<meta content=...>`), senza `Movie` annidato.

Le funzioni ricevono l'HTML già scaricato e non fanno I/O: sono pure e testabili
a fixture. Il filtro per data resta nel connettore (vedi `filter_films_to_dates`).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import html
import json
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from scraper.models import Film, Showing
from scraper.normalizer import normalize_genres, normalize_title

logger = logging.getLogger(__name__)

# Durata ISO 8601 schema.org: "PT107M", "PT1H49M", "PT1H49M30S" (le frazioni < 30s
# sono ignorate, coerente con normalize_duration).
_ISO_DURATION_RE = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", re.IGNORECASE)

# Campi del `Movie` che il builder copia la prima volta che li trova.
_MOVIE_META_FIELDS = ("poster", "description", "director", "duration", "source_url")


def extract_screening_events(html_text: str, base_url: str, cinema: str = "", cinema_slug: str = "") -> list[Film]:
    """Estrae Film con `present_in` da una pagina con Movie+ScreeningEvent.

    Prova prima il JSON-LD: se contiene `ScreeningEvent` usa quella via,
    altrimenti ripiega sui microdata. NON filtra per data: restituisce tutto ciò
    che la pagina espone. Non fa I/O.

    Args:
        html_text: HTML della pagina, già scaricato.
        base_url: URL della pagina, per risolvere link/immagini relativi.
        cinema: nome del cinema da assegnare agli Showing (se omesso si tenta dal
            `location.name` del markup).
        cinema_slug: slug del cinema da assegnare agli Showing.
    """
    return SchemaOrgExtractor(base_url=base_url, cinema=cinema, cinema_slug=cinema_slug).extract_screening_events(
        html_text
    )


def extract_jsonld_graph(html_text: str) -> list[dict]:
    """Ritorna il `@graph` (o la lista di oggetti) dei soli `<script ld+json>` che
    contengono almeno un `ScreeningEvent`. Lista vuota se assenti o malformati.
    """
    return SchemaOrgExtractor().extract_jsonld_graph(html_text)


def extract_microdata_items(html_text: str, type_: str) -> list[Tag]:
    """Tutti gli elementi con `itemtype` schema.org/<type_>, a qualsiasi livello di annidamento."""
    return SchemaOrgExtractor().extract_microdata_items(html_text, type_)


def filter_films_to_dates(films: list[Film], dates: list[str] | None) -> list[Film]:
    """Tiene solo gli spettacoli nelle date richieste; scarta i Film senza spettacoli residui.

    `dates=None` → nessun filtro. Ritorna nuovi `Film` (gli argomenti non sono
    mutati). La chiama il connettore, non l'estrattore.
    """
    if dates is None:
        return list(films)
    wanted = set(dates)
    filtered: list[Film] = []
    for film in films:
        kept = [showing for showing in film.present_in if showing.date in wanted]
        if kept:
            filtered.append(replace(film, present_in=kept))
    return filtered


class SchemaOrgExtractor:
    """Parametrizza l'estrazione schema.org con il contesto del cinema.

    La classe è il punto di estensione per i connettori (che passano nome e slug);
    le funzioni a livello di modulo sono la comoda API senza stato per i test.
    """

    def __init__(self, base_url: str = "", cinema: str = "", cinema_slug: str = "") -> None:
        self.base_url = base_url
        self.cinema = cinema
        self.cinema_slug = cinema_slug

    def extract_screening_events(self, html_text: str) -> list[Film]:
        """Vedi `extract_screening_events` a livello di modulo."""
        soup = BeautifulSoup(html_text, "lxml")
        graph = _extract_jsonld_graph(soup)
        events = [item for item in graph if "ScreeningEvent" in _types_of(item)]
        if events:
            return self._films_from_jsonld(graph, events)
        return self._films_from_microdata(soup)

    def extract_jsonld_graph(self, html_text: str) -> list[dict]:
        """Vedi `extract_jsonld_graph` a livello di modulo."""
        return _extract_jsonld_graph(BeautifulSoup(html_text, "lxml"))

    def extract_microdata_items(self, html_text: str, type_: str) -> list[Tag]:
        """Vedi `extract_microdata_items` a livello di modulo."""
        return _microdata_items(BeautifulSoup(html_text, "lxml"), type_)

    # --- via JSON-LD -------------------------------------------------------

    def _films_from_jsonld(self, graph: list[dict], events: list[dict]) -> list[Film]:
        movies = {
            item["@id"]: item for item in graph if "Movie" in _types_of(item) and isinstance(item.get("@id"), str)
        }
        films_by_key: dict[str, dict] = {}
        for event in events:
            parsed = _parse_start_date(event.get("startDate"))
            if parsed is None:
                continue
            date, time = parsed
            data = _jsonld_event_movie_data(event, movies, self.base_url)
            _collect_event(films_by_key, data, date, time, self.cinema)
        return _build_films(films_by_key, self.base_url, self.cinema, self.cinema_slug)

    # --- via microdata -----------------------------------------------------

    def _films_from_microdata(self, soup: BeautifulSoup) -> list[Film]:
        films_by_key: dict[str, dict] = {}
        for event in _microdata_items(soup, "ScreeningEvent"):
            parsed = _microdata_start_date(event)
            if parsed is None:
                continue
            date, time = parsed
            data = _microdata_event_movie_data(event, self.base_url)
            _collect_event(films_by_key, data, date, time, self.cinema)
        return _build_films(films_by_key, self.base_url, self.cinema, self.cinema_slug)


# ---------------------------------------------------------------------------
# JSON-LD helpers
# ---------------------------------------------------------------------------


def _extract_jsonld_graph(soup: BeautifulSoup) -> list[dict]:
    graph: list[dict] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string if script.string is not None else script.get_text()
        if not raw or not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except ValueError as exc:
            logger.debug("JSON-LD malformato ignorato: %s", exc)
            continue
        items = _flatten_jsonld(data)
        if any("ScreeningEvent" in _types_of(item) for item in items):
            graph.extend(items)
    return graph


def _flatten_jsonld(data: object) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        nested = data.get("@graph")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        return [data]
    return []


def _types_of(item: object) -> list[str]:
    if not isinstance(item, dict):
        return []
    value = item.get("@type")
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)] if value else []


def _jsonld_event_movie_data(event: dict, movies: dict[str, dict], base_url: str) -> dict:
    work = event.get("workPresented")
    movie: dict | None = None
    if isinstance(work, dict):
        movie = movies.get(work.get("@id")) if isinstance(work.get("@id"), str) else None
        if movie is None:
            movie = work
    data = _jsonld_movie_data(movie, base_url) if movie is not None else {}
    if not data.get("title"):
        data["title"] = _jsonld_text(work) if not isinstance(work, dict) else None
    if not data.get("title"):
        data["title"] = _jsonld_text(event.get("name"))
    location = event.get("location")
    data["location_name"] = _jsonld_text(location.get("name")) if isinstance(location, dict) else None
    return data


def _jsonld_movie_data(movie: dict, base_url: str) -> dict:
    return {
        "title": _jsonld_text(movie.get("name")),
        "source_url": _absolute(_jsonld_text(movie.get("@id") or movie.get("url")), base_url),
        "poster": _absolute(_jsonld_text(movie.get("image")), base_url),
        "description": _jsonld_text(movie.get("description")),
        "director": _jsonld_text(movie.get("director")),
        "duration": _jsonld_text(movie.get("duration")),
        "year": _parse_year(movie.get("dateCreated") or movie.get("datePublished")),
        "genres": normalize_genres(movie.get("genre")),
    }


def _jsonld_text(value: object) -> str | None:
    """Estrae una stringa da un valore JSON-LD che può essere str, lista o oggetto."""
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("name") or value.get("url")
        return html.unescape(str(value).strip()) if value else None
    if isinstance(value, list):
        return _jsonld_text(value[0]) if value else None
    text = str(value).strip()
    return html.unescape(text) if text else None


# ---------------------------------------------------------------------------
# Microdata helpers
# ---------------------------------------------------------------------------


def _microdata_items(soup: BeautifulSoup, type_: str) -> list[Tag]:
    return [el for el in soup.find_all(attrs={"itemtype": True}) if _itemtype_matches(el.get("itemtype"), type_)]


def _itemtype_matches(itemtype: object, type_: str) -> bool:
    if itemtype is None:
        return False
    raw_values = itemtype if isinstance(itemtype, list) else [itemtype]
    for raw in raw_values:
        for candidate in str(raw).split():
            if candidate.rstrip("/").rsplit("/", 1)[-1] == type_:
                return True
    return False


def _own_props(item: Tag) -> list[Tag]:
    """Discendenti con `itemprop` che appartengono a questo item.

    Microdata: una proprietà appartiene all'`itemscope` più vicino. Qui si scartano
    gli elementi il cui antenato `itemscope` più vicino è un item annidato (es. il
    `Movie` dentro `workPresented`), così `Movie` e `ScreeningEvent` non si rubano i campi.
    """
    props: list[Tag] = []
    for el in item.find_all(attrs={"itemprop": True}):
        owner = _nearest_itemscope(el, stop=item)
        if owner is None:
            props.append(el)
    return props


def _nearest_itemscope(el: Tag, stop: Tag) -> Tag | None:
    parent = el.parent
    while parent is not None and parent is not stop:
        if isinstance(parent, Tag) and parent.has_attr("itemscope"):
            return parent
        parent = parent.parent
    return None


def _has_itemprop(el: Tag, prop: str) -> bool:
    value = el.get("itemprop")
    values = value if isinstance(value, list) else [value]
    return any(prop == str(v) for v in values if v)


def _prop_elements(item: Tag, prop: str) -> list[Tag]:
    return [el for el in _own_props(item) if _has_itemprop(el, prop)]


def _first_value(item: Tag, prop: str) -> str | None:
    elements = _prop_elements(item, prop)
    return _prop_value(elements[0]) if elements else None


def _all_values(item: Tag, prop: str) -> list[str]:
    return [value for value in (_prop_value(el) for el in _prop_elements(item, prop)) if value]


def _prop_value(el: Tag) -> str | None:
    """Valore di una proprietà microdata secondo le regole schema.org + tema Ummon.

    I temi `zen25`/`concordia` mettono `content=` anche su `<div>`/`<span>` (fuori
    standard): va letto per primo, altrimenti si degrada al testo dell'elemento.
    """
    content = _attr_str(el, "content")
    if content:
        return html.unescape(content)
    name = el.name.lower()
    if name in ("a", "area", "link"):
        value = _attr_str(el, "href")
    elif name in ("img", "audio", "video", "embed", "iframe", "source", "track"):
        value = _attr_str(el, "src")
    elif name == "time":
        value = _attr_str(el, "datetime") or el.get_text(strip=True)
    elif name == "data":
        value = _attr_str(el, "value")
    else:
        value = el.get_text(" ", strip=True)
    return html.unescape(value) if value else None


def _attr_str(el: Tag, name: str) -> str | None:
    value = el.get(name)
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value) if value else None


def _ancestor_movie(el: Tag) -> Tag | None:
    parent = el.parent
    while parent is not None:
        if isinstance(parent, Tag) and _itemtype_matches(parent.get("itemtype"), "Movie"):
            return parent
        parent = parent.parent
    return None


def _microdata_start_date(event: Tag) -> tuple[str, str] | None:
    value = _first_value(event, "startDate")
    return _parse_start_date(value)


def _microdata_event_movie_data(event: Tag, base_url: str) -> dict:
    work = _first_value_element(event, "workPresented")
    data: dict = {}
    if work is not None and work.has_attr("itemscope") and _itemtype_matches(work.get("itemtype"), "Movie"):
        data = _microdata_movie_data(work, base_url)
    elif work is not None:
        data = {"title": _prop_value(work)}

    ancestor = _ancestor_movie(event)
    if ancestor is not None and ancestor is not work:
        data = _merge_movie_data(data, _microdata_movie_data(ancestor, base_url))

    if not data.get("title"):
        data["title"] = _first_value(event, "name")
    location = _first_value_element(event, "location")
    if location is not None:
        data["location_name"] = _first_value(location, "name")
    return data


def _first_value_element(item: Tag, prop: str) -> Tag | None:
    elements = _prop_elements(item, prop)
    return elements[0] if elements else None


def _microdata_movie_data(movie: Tag, base_url: str) -> dict:
    return {
        "title": _first_value(movie, "name"),
        "source_url": _absolute(_first_value(movie, "url"), base_url),
        "poster": _absolute(_first_value(movie, "image"), base_url),
        "description": _first_value(movie, "description"),
        "director": _first_value(movie, "director"),
        "duration": _first_value(movie, "duration"),
        "year": _parse_year(_first_value(movie, "dateCreated")),
        "genres": normalize_genres(_all_values(movie, "genre")),
    }


def _merge_movie_data(primary: dict, secondary: dict) -> dict:
    """Completa `primary` con i campi mancanti di `secondary` (senza mutare gli input)."""
    merged = dict(primary)
    for field in _MOVIE_META_FIELDS + ("title", "year"):
        if not merged.get(field) and secondary.get(field):
            merged[field] = secondary[field]
    if not merged.get("genres") and secondary.get("genres"):
        merged["genres"] = list(secondary["genres"])
    return merged


# ---------------------------------------------------------------------------
# Film builder
# ---------------------------------------------------------------------------


def _collect_event(films_by_key: dict[str, dict], data: dict, date: str, time: str, cinema: str) -> None:
    title = (data.get("title") or "").strip()
    if not title:
        return
    key = normalize_title(title)
    if not key:
        return

    entry = films_by_key.get(key)
    if entry is None:
        entry = {"title": title, "meta": {}, "showings": {}}
        films_by_key[key] = entry
    for field in _MOVIE_META_FIELDS:
        if not entry["meta"].get(field) and data.get(field):
            entry["meta"][field] = data[field]
    if data.get("year") and not entry["meta"].get("year"):
        entry["meta"]["year"] = data["year"]
    if data.get("genres") and not entry["meta"].get("genres"):
        entry["meta"]["genres"] = list(data["genres"])
    if not entry["meta"].get("cinema"):
        entry["meta"]["cinema"] = cinema or data.get("location_name")

    times = entry["showings"].setdefault(date, [])
    if time and time not in times:
        times.append(time)


def _build_films(films_by_key: dict[str, dict], base_url: str, cinema: str, cinema_slug: str) -> list[Film]:
    films: list[Film] = []
    for key, entry in films_by_key.items():
        meta = entry["meta"]
        resolved_cinema = cinema or meta.get("cinema") or ""
        showings = [
            Showing(
                cinema=resolved_cinema,
                cinema_slug=cinema_slug,
                date=date,
                times=sorted(entry["showings"][date]),
                source_url=meta.get("source_url"),
            )
            for date in sorted(entry["showings"])
        ]
        films.append(
            Film(
                title=entry["title"],
                title_normalized=key,
                present_in=showings,
                source_poster=meta.get("poster"),
                description=meta.get("description"),
                genres=meta.get("genres") or [],
                director=meta.get("director"),
                duration=_iso_duration_to_minutes(meta.get("duration")),
                year=meta.get("year"),
            )
        )
    return films


# ---------------------------------------------------------------------------
# Normalizzazione valori
# ---------------------------------------------------------------------------


def _parse_start_date(value: object) -> tuple[str, str] | None:
    """`2026-09-20T18:30:00+02:00` → `("2026-09-20", "18:30")`; None se illeggibile."""
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        logger.debug("startDate non parsabile: %r", value)
        return None
    return parsed.strftime("%Y-%m-%d"), parsed.strftime("%H:%M")


def _iso_duration_to_minutes(value: object) -> str | None:
    """`PT107M`/`PT1H49M` → `"107 min"`/`"109 min"`; passthrough se già umano."""
    if not value:
        return None
    text = str(value).strip()
    if not text.upper().startswith("PT"):
        return text
    match = _ISO_DURATION_RE.match(text)
    if match is None:
        # Prefisso ISO ma corpo irriconoscibile (es. "PTM" nel dato reale di Zenith):
        # meglio nessuna durata che una stringa che normalize_duration scarterebbe comunque.
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total = hours * 60 + minutes + (1 if seconds >= 30 else 0)
    return f"{total} min" if total else None


def _parse_year(value: object) -> int | None:
    if not value:
        return None
    match = re.search(r"(?:19|20)\d{2}", str(value))
    return int(match.group(0)) if match else None


def _absolute(url: str | None, base_url: str) -> str | None:
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    if base_url:
        return urljoin(base_url, url)
    return url
