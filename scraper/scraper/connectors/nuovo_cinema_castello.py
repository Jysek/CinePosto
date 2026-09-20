"""Connettore Nuovo Cinema Castello: JSON-LD della homepage, un'unica richiesta.

Fonte primaria: la homepage (`nuovocinemacastello.it`) espone nel `<head>` un
`@graph` JSON-LD con i `Movie` e gli `ScreeningEvent` della settimana. Stesso
tema `zen25` di Cinema Zenith, quindi nessun parser dedicato: l'adattatore
scarica l'HTML e delega a `SchemaOrgExtractor`.

Il sito non ha una pagina settimanale equivalente a `programmazione-settimana`
di Zenith: il fallback (dettaglio film, una richiesta per film) resta per
l'ondata 1.1. Per l'MVP la sola homepage basta.
"""

from __future__ import annotations

import logging

import requests

from scraper.config import (
    NUOVO_CASTELLO_BASE_URL,
    NUOVO_CASTELLO_NAME,
    NUOVO_CASTELLO_SLUG,
    NUOVO_CASTELLO_URL,
    PROJECT_USER_AGENT,
    get_week_dates,
)
from scraper.connectors.base import BaseConnector
from scraper.connectors.schema_org import extract_screening_events, filter_films_to_dates
from scraper.errors import make_error
from scraper.http import retry_request
from scraper.models import CinemaError, Film, ScrapeResult

logger = logging.getLogger(__name__)


class NuovoCinemaCastelloConnector(BaseConnector):
    """Connettore sottile: scarica la homepage e delega all'estrattore condiviso."""

    @property
    def cinema_name(self) -> str:
        """Nome pubblico del cinema (da config)."""
        return NUOVO_CASTELLO_NAME

    @property
    def cinema_slug(self) -> str:
        """Slug stabile del cinema (da config)."""
        return NUOVO_CASTELLO_SLUG

    def scrape(self, today: str, dates: list[str] | None = None) -> ScrapeResult:
        """Estrae la programmazione dalla homepage.

        Gli errori di rete/parsing non sollevano: finiscono in `ScrapeResult.errors`
        così una fonte rotta non blocca la run complessiva.
        """
        target_dates = dates or get_week_dates()
        errors: list[CinemaError] = []
        session = requests.Session()
        session.headers.update({"User-Agent": PROJECT_USER_AGENT, "Accept-Language": "it-IT,it;q=0.9"})

        try:
            page_html = retry_request("get", NUOVO_CASTELLO_URL, session, label="CASTELLO").text
            films = self._extract(page_html)
        except Exception as exc:
            logger.error("Castello scrape failed: %s", exc, exc_info=True)
            errors.append(make_error(self.cinema_name, exc, "scrape", url=NUOVO_CASTELLO_URL))
            return ScrapeResult(errors=errors)

        return ScrapeResult(films=filter_films_to_dates(films, target_dates), errors=errors)

    def _extract(self, page_html: str) -> list[Film]:
        """Delega all'estrattore condiviso, passando il contesto del cinema."""
        return extract_screening_events(
            page_html,
            NUOVO_CASTELLO_BASE_URL,
            cinema=self.cinema_name,
            cinema_slug=self.cinema_slug,
        )

    def fetch_film_detail(self, film_url: str) -> dict | None:
        """Metadati extra non necessari per l'MVP: la homepage li porta già."""
        return None
