"""Connettore Cinema Metropolis: scoperta in due fasi (homepage → pagina film).

La homepage di `cinemametropolis.it` espone i film **in programmazione** con
microdata `Movie` ma **senza orari** (0 `ScreeningEvent`, verificato il 19/09/2026).
La settimana completa sta nelle pagine di dettaglio `/films/<slug>/`: stesso
vocabolario microdata di Concordia (`[itemprop=startDate][content]`), quindi
nessun parser dedicato — l'adattatore scopre gli URL dalla homepage e delega ogni
pagina a `SchemaOrgExtractor`.

Perché due fasi (e non `films-sitemap.xml`): la sitemap contiene ~500 film storici,
non la programmazione corrente. La lista dei film attuali è **solo** quella linkata
dalla homepage; la sitemap non viene mai richiesta.

Un errore su una pagina film non ferma le altre: finisce in `ScrapeResult.errors`
(come fa `thespace.py` per data) così una pagina rotta non fa cadere il cinema.
Costo: 1 richiesta homepage + N pagine film per run giornaliera.
"""

from __future__ import annotations

from dataclasses import replace
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import requests

from scraper.config import (
    METROPOLIS_BASE_URL,
    METROPOLIS_NAME,
    METROPOLIS_SLUG,
    METROPOLIS_URL,
    PROJECT_USER_AGENT,
    get_week_dates,
)
from scraper.connectors.base import BaseConnector
from scraper.connectors.schema_org import extract_screening_events, filter_films_to_dates
from scraper.errors import make_error
from scraper.http import retry_request
from scraper.models import CinemaError, Film, ScrapeResult, Showing

logger = logging.getLogger(__name__)

# Pagina di dettaglio film: `/films/<slug>/`. Esclude l'indice `/films/` e la
# sitemap storica `films-sitemap.xml` (path diverso), usata solo come archivio.
_FILM_PATH_RE = re.compile(r"^/films/[^/]+/?$")


class CinemaMetropolisConnector(BaseConnector):
    """Connettore a due fasi: homepage per la lista film, dettaglio per gli orari."""

    @property
    def cinema_name(self) -> str:
        """Nome pubblico del cinema (da config)."""
        return METROPOLIS_NAME

    @property
    def cinema_slug(self) -> str:
        """Slug stabile del cinema (da config)."""
        return METROPOLIS_SLUG

    def scrape(self, today: str, dates: list[str] | None = None) -> ScrapeResult:
        """Scopre i film correnti dalla homepage e ne legge gli orari a pagina per pagina.

        Gli errori di rete/parsing non sollevano: un errore sulla homepage chiude la
        run del connettore con un `ScrapeResult` di soli errori; un errore su una
        pagina film viene registrato e si prosegue con le altre.
        """
        target_dates = dates or get_week_dates()
        errors: list[CinemaError] = []
        session = requests.Session()
        session.headers.update({"User-Agent": PROJECT_USER_AGENT, "Accept-Language": "it-IT,it;q=0.9"})

        try:
            home_html = retry_request("get", METROPOLIS_URL, session, label="METROPOLIS").text
            film_urls = self._collect_film_urls(home_html)
        except Exception as exc:
            logger.error("Metropolis scrape failed: %s", exc, exc_info=True)
            errors.append(make_error(self.cinema_name, exc, "scrape", url=METROPOLIS_URL))
            return ScrapeResult(errors=errors)

        by_title: dict[str, Film] = {}
        for film_url in film_urls:
            try:
                page_html = retry_request("get", film_url, session, label="METROPOLIS").text
                _accumulate_films(by_title, self._extract(page_html, film_url))
            except Exception as exc:
                logger.warning("Metropolis detail failed for %s: %s", film_url, exc)
                errors.append(make_error(self.cinema_name, exc, "detail", url=film_url))

        return ScrapeResult(films=filter_films_to_dates(list(by_title.values()), target_dates), errors=errors)

    def _collect_film_urls(self, home_html: str) -> list[str]:
        """URL unici `/films/<slug>/` linkati dalla homepage (niente sitemap storica).

        Legge sia i `meta[itemprop=url]` delle card `Movie` sia gli `<a href>`, così
        regge i piccoli restyling del tema `postmetro`. L'ordine di apparizione è
        preservato e i duplicati (slider) vengono scartati.
        """
        soup = BeautifulSoup(home_html, "lxml")
        urls: list[str] = []
        seen: set[str] = set()
        for el in soup.find_all(attrs={"itemprop": "url"}):
            _register_film_url(_attr_first(el, "content") or _attr_first(el, "href"), urls, seen)
        for anchor in soup.find_all("a", href=True):
            _register_film_url(_attr_first(anchor, "href"), urls, seen)
        return urls

    def _extract(self, page_html: str, page_url: str) -> list[Film]:
        """Delega all'estrattore condiviso, passando il contesto del cinema."""
        return extract_screening_events(
            page_html,
            page_url,
            cinema=self.cinema_name,
            cinema_slug=self.cinema_slug,
        )

    def fetch_film_detail(self, film_url: str) -> dict | None:
        """Metadati extra non necessari: la pagina di dettaglio li porta già tutti."""
        return None


def _attr_first(el, name: str) -> str | None:
    """Primo valore stringa dell'attributo `name` (BeautifulSoup può restituire liste)."""
    value = el.get(name)
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value) if value else None


def _register_film_url(candidate: str | None, urls: list[str], seen: set[str]) -> None:
    """Aggiunge l'URL se è una pagina film assoluta del sito; ignora il resto."""
    url = _film_url(candidate)
    if url is None:
        return
    key = url.rstrip("/")
    if key in seen:
        return
    seen.add(key)
    urls.append(url)


def _film_url(candidate: str | None) -> str | None:
    """Normalizza un link a `/films/<slug>/`; None se non è una pagina film del sito."""
    if not candidate:
        return None
    absolute = urljoin(METROPOLIS_BASE_URL + "/", candidate.strip())
    parsed = urlparse(absolute)
    if parsed.netloc != urlparse(METROPOLIS_BASE_URL).netloc:
        return None
    if not _FILM_PATH_RE.match(parsed.path):
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _accumulate_films(by_title: dict[str, Film], films: list[Film]) -> None:
    """Fonde i Film per `title_normalized` senza mutare quelli già accumulati.

    Ogni pagina di dettaglio produce un solo Film, ma lo stesso titolo può
    comparire su più pagine: gli spettacoli vengono uniti per (data, cinema, sala).
    """
    for film in films:
        existing = by_title.get(film.title_normalized)
        if existing is None:
            by_title[film.title_normalized] = film
            continue
        by_title[film.title_normalized] = replace(
            existing,
            present_in=_merge_showings(existing.present_in, film.present_in),
        )


def _merge_showings(old: list[Showing], new: list[Showing]) -> list[Showing]:
    """Unisce due liste di Showing per (data, cinema, sala), unendo gli orari ordinati."""
    merged: dict[tuple[str, str, str], Showing] = {}
    for showing in [*old, *new]:
        key = (showing.date, showing.cinema, showing.screen or "")
        current = merged.get(key)
        if current is None:
            merged[key] = replace(showing, times=list(showing.times))
        else:
            merged[key] = replace(current, times=sorted(set(current.times) | set(showing.times)))
    return sorted(merged.values(), key=lambda s: (s.date, s.cinema))
