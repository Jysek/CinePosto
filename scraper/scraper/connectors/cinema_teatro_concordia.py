"""Connettore Cinema Teatro Concordia: microdata della homepage, un'unica richiesta.

Fonte primaria: la homepage (`www.cineconcordia.it`) espone la programmazione
in **microdata schema.org** (`div[itemprop=startDate][content]`), annidata in
`div[itemscope][itemtype='http://schema.org/ScreeningEvent']`. È la variante
"microdata" dello stesso vocabolario di Zenith/Castello, quindi nessun parser
dedicato: l'adattatore scarica l'HTML e delega a `SchemaOrgExtractor`.

Il tema `concordia` duplica il `Movie` a livello superiore (`w_film_cont`) e
dentro `workPresented`, con `itemtype` a **apici singoli**: se ne occupa
l'estrattore condiviso (merge per campo, dedup del Film per titolo normalizzato).

I metadati umani del dettaglio film (`div.film_data`, es. genere) non servono
all'MVP: la homepage porta già titolo, durata, regia, poster e URL.
"""

from __future__ import annotations

import logging

import requests

from scraper.config import (
    CONCORDIA_BASE_URL,
    CONCORDIA_NAME,
    CONCORDIA_SLUG,
    CONCORDIA_URL,
    PROJECT_USER_AGENT,
    get_week_dates,
)
from scraper.connectors.base import BaseConnector
from scraper.connectors.schema_org import extract_screening_events, filter_films_to_dates
from scraper.errors import make_error
from scraper.http import retry_request
from scraper.models import CinemaError, Film, ScrapeResult

logger = logging.getLogger(__name__)


class CinemaTeatroConcordiaConnector(BaseConnector):
    """Connettore sottile: scarica la homepage e delega all'estrattore condiviso."""

    @property
    def cinema_name(self) -> str:
        """Nome pubblico del cinema (da config)."""
        return CONCORDIA_NAME

    @property
    def cinema_slug(self) -> str:
        """Slug stabile del cinema (da config)."""
        return CONCORDIA_SLUG

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
            page_html = retry_request("get", CONCORDIA_URL, session, label="CONCORDIA").text
            films = self._extract(page_html)
        except Exception as exc:
            logger.error("Concordia scrape failed: %s", exc, exc_info=True)
            errors.append(make_error(self.cinema_name, exc, "scrape", url=CONCORDIA_URL))
            return ScrapeResult(errors=errors)

        return ScrapeResult(films=filter_films_to_dates(films, target_dates), errors=errors)

    def _extract(self, page_html: str) -> list[Film]:
        """Delega all'estrattore condiviso, passando il contesto del cinema."""
        return extract_screening_events(
            page_html,
            CONCORDIA_BASE_URL,
            cinema=self.cinema_name,
            cinema_slug=self.cinema_slug,
        )

    def fetch_film_detail(self, film_url: str) -> dict | None:
        """Metadati extra non necessari per l'MVP: la homepage li porta già."""
        return None
