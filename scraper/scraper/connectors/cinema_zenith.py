"""Connettore Cinema Zenith: JSON-LD della homepage, con fallback alla pagina settimana.

Fonte primaria: la homepage (`cinemazenith.it`) espone nel `<head>` un `@graph`
JSON-LD con tutti i `Movie` e gli `ScreeningEvent` della settimana. Se la pagina
non contiene spettacoli (cache stantia o restyling) si ripiega su
`/programmazione-settimana/`, che ripete la stessa settimana in microdata.
"""

from __future__ import annotations

import logging

import requests

from scraper.config import (
    CINEMA_ZENITH_BASE_URL,
    CINEMA_ZENITH_NAME,
    CINEMA_ZENITH_SLUG,
    CINEMA_ZENITH_URL,
    CINEMA_ZENITH_WEEK_URL,
    PROJECT_USER_AGENT,
    get_week_dates,
)
from scraper.connectors.base import BaseConnector
from scraper.connectors.schema_org import extract_screening_events, filter_films_to_dates
from scraper.errors import make_error
from scraper.http import retry_request
from scraper.models import CinemaError, Film, ScrapeResult

logger = logging.getLogger(__name__)


class CinemaZenithConnector(BaseConnector):
    """Connettore sottile: scarica l'HTML e delega a `SchemaOrgExtractor`."""

    @property
    def cinema_name(self) -> str:
        """Nome pubblico del cinema (da config)."""
        return CINEMA_ZENITH_NAME

    @property
    def cinema_slug(self) -> str:
        """Slug stabile del cinema (da config)."""
        return CINEMA_ZENITH_SLUG

    def scrape(self, today: str, dates: list[str] | None = None) -> ScrapeResult:
        """Estrae la programmazione della homepage; se vuota ripiega sulla settimana.

        Gli errori di rete/parsing non sollevano: finiscono in `ScrapeResult.errors`
        così una fonte rotta non blocca la run complessiva.
        """
        target_dates = dates or get_week_dates()
        errors: list[CinemaError] = []
        session = requests.Session()
        session.headers.update({"User-Agent": PROJECT_USER_AGENT, "Accept-Language": "it-IT,it;q=0.9"})

        last_url = CINEMA_ZENITH_URL
        try:
            films = self._extract(retry_request("get", CINEMA_ZENITH_URL, session, label="ZENITH").text)
            if not films:
                logger.info("Zenith: nessuno spettacolo in homepage, provo %s", CINEMA_ZENITH_WEEK_URL)
                last_url = CINEMA_ZENITH_WEEK_URL
                films = self._extract(retry_request("get", CINEMA_ZENITH_WEEK_URL, session, label="ZENITH").text)
        except Exception as exc:
            logger.error("Zenith scrape failed: %s", exc, exc_info=True)
            errors.append(make_error(self.cinema_name, exc, "scrape", url=last_url))
            return ScrapeResult(errors=errors)

        return ScrapeResult(films=filter_films_to_dates(films, target_dates), errors=errors)

    def _extract(self, page_html: str) -> list[Film]:
        """Delega all'estrattore condiviso, passando il contesto del cinema."""
        return extract_screening_events(
            page_html,
            CINEMA_ZENITH_BASE_URL,
            cinema=self.cinema_name,
            cinema_slug=self.cinema_slug,
        )

    def fetch_film_detail(self, film_url: str) -> dict | None:
        """Metadati extra non necessari per l'MVP: la homepage li porta già."""
        return None
