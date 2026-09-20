"""Test del connettore Cinema Metropolis: scoperta in due fasi su fixture reali.

Fixture registrate **una volta sola** (2026-09-19) con lo User-Agent del progetto:
`metropolis_home.html` (card `Movie` senza orari + link alla sitemap storica) e
`metropolis_film_serpenti.html` (la settimana in microdata `ScreeningEvent`).
La homepage **non** contiene orari: gli orari arrivano solo dalle pagine
`/films/<slug>/`, quindi i test contano anche le richieste effettuate.
Se il sito cambia markup le fixture vanno ri-registrate.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import responses

from scraper.config import METROPOLIS_URL, PROJECT_USER_AGENT
from scraper.connectors.cinema_metropolis import CinemaMetropolisConnector
from scraper.models import Film

FIXTURES = Path(__file__).parent / "fixtures"

TODAY = "2026-09-19"
DATES = ["2026-09-19", "2026-09-20", "2026-09-23", "2026-09-24"]

SERPENTI_URL = "https://www.cinemametropolis.it/films/serpenti/"
NAZA_URL = "https://www.cinemametropolis.it/films/naza/"
SITEMAP_URL = "https://www.cinemametropolis.it/films-sitemap.xml"

# Pagina Naza minima: serve solo a coprire il secondo film linkato dalla homepage.
NAZA_HTML = """
<html><body>
<li itemscope itemtype="http://schema.org/ScreeningEvent">
  <meta itemprop="name" content="Naza"/>
  <div itemprop="workPresented" itemscope itemtype="http://schema.org/Movie">
    <meta itemprop="name" content="Naza"/>
    <meta itemprop="url" content="https://www.cinemametropolis.it/films/naza/"/>
    <meta itemprop="duration" content="PT95M"/>
  </div>
  <div itemprop="startDate" content="2026-09-24T16:00:00+02:00">16:00</div>
</li>
</body></html>
"""


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _by_title(films: list[Film], title: str) -> Film:
    return next(film for film in films if film.title == title)


def _register_concrete_pages() -> None:
    """Homepage + le due pagine film correnti, ciascuna con una sola richiesta."""
    responses.add(responses.GET, METROPOLIS_URL, body=_load("metropolis_home.html"), status=200)
    responses.add(responses.GET, SERPENTI_URL, body=_load("metropolis_film_serpenti.html"), status=200)
    responses.add(responses.GET, NAZA_URL, body=NAZA_HTML, status=200)


@responses.activate
def test_collects_current_film_urls_from_homepage():
    _register_concrete_pages()

    result = CinemaMetropolisConnector().scrape(TODAY, dates=DATES)

    requested = [call.request.url for call in responses.calls]
    # Una richiesta per pagina, niente duplicati nonostante lo slider ripeta le card.
    assert requested == [METROPOLIS_URL, SERPENTI_URL, NAZA_URL]
    assert {film.title for film in result.films} == {"Serpenti", "Naza"}
    assert result.errors == []


@responses.activate
def test_ignores_films_sitemap_archive():
    archive_url = "https://www.cinemametropolis.it/films/vecchio-classico-1954/"
    sitemap_xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset><url><loc>{archive_url}</loc></url></urlset>'
    _register_concrete_pages()
    responses.add(responses.GET, SITEMAP_URL, body=sitemap_xml, status=200)

    result = CinemaMetropolisConnector().scrape(TODAY, dates=DATES)

    requested = [call.request.url for call in responses.calls]
    assert SITEMAP_URL not in requested
    assert archive_url not in requested
    assert {film.title for film in result.films} == {"Serpenti", "Naza"}


@responses.activate
def test_extracts_week_screenings_from_film_detail():
    _register_concrete_pages()

    result = CinemaMetropolisConnector().scrape(TODAY, dates=DATES)
    serpenti = _by_title(result.films, "Serpenti")

    assert {showing.date for showing in serpenti.present_in} == {"2026-09-19", "2026-09-20", "2026-09-23"}
    assert sum(len(showing.times) for showing in serpenti.present_in) == 4
    assert serpenti.duration == "88 min"
    assert serpenti.director == "Roberto De Paolis"
    assert serpenti.source_poster == "https://www.cinemametropolis.it/wp-content/uploads/2026/09/serpenti-1.jpg"
    assert {showing.source_url for showing in serpenti.present_in} == {SERPENTI_URL}


@responses.activate
def test_parses_start_date_from_content_attribute():
    _register_concrete_pages()

    result = CinemaMetropolisConnector().scrape(TODAY, dates=DATES)
    by_date = {showing.date: showing.times for showing in _by_title(result.films, "Serpenti").present_in}

    assert by_date["2026-09-19"] == ["18:30", "21:00"]
    assert by_date["2026-09-20"] == ["18:30"]
    assert by_date["2026-09-23"] == ["21:00"]


@responses.activate
def test_decodes_html_entities_in_description():
    _register_concrete_pages()

    result = CinemaMetropolisConnector().scrape(TODAY, dates=DATES)

    description = _by_title(result.films, "Serpenti").description
    assert description is not None
    assert "&#" not in description
    assert "è" in description and "giudiziario" in description


@responses.activate
def test_continues_when_one_film_detail_fails():
    responses.add(responses.GET, METROPOLIS_URL, body=_load("metropolis_home.html"), status=200)
    responses.add(responses.GET, SERPENTI_URL, body=_load("metropolis_film_serpenti.html"), status=200)
    responses.add(responses.GET, NAZA_URL, status=500)

    with mock.patch("scraper.http.time.sleep", return_value=None):
        result = CinemaMetropolisConnector().scrape(TODAY, dates=DATES)

    assert {film.title for film in result.films} == {"Serpenti"}
    assert len(result.errors) == 1
    assert result.errors[0].cinema == "Cinema Metropolis"
    assert result.errors[0].phase == "detail"
    assert result.errors[0].url == NAZA_URL


@responses.activate
def test_filters_events_outside_requested_dates():
    _register_concrete_pages()

    result = CinemaMetropolisConnector().scrape(TODAY, dates=["2026-09-20"])

    # Naza ha spettacoli solo il 24: senza spettacoli nella finestra va scartato.
    assert {film.title for film in result.films} == {"Serpenti"}
    assert _by_title(result.films, "Serpenti").present_in[0].times == ["18:30"]


@responses.activate
def test_sends_project_user_agent():
    _register_concrete_pages()

    CinemaMetropolisConnector().scrape(TODAY, dates=DATES)

    assert responses.calls
    assert all(call.request.headers["User-Agent"] == PROJECT_USER_AGENT for call in responses.calls)


@responses.activate
def test_returns_error_result_when_homepage_unreachable():
    responses.add(responses.GET, METROPOLIS_URL, status=503)

    with mock.patch("scraper.http.time.sleep", return_value=None):
        result = CinemaMetropolisConnector().scrape(TODAY, dates=DATES)

    assert result.films == []
    assert len(result.errors) == 1
    assert result.errors[0].cinema == "Cinema Metropolis"
    assert result.errors[0].phase == "scrape"
    assert result.errors[0].url == METROPOLIS_URL


def test_fetch_film_detail_is_not_needed():
    connector = CinemaMetropolisConnector()

    assert connector.fetch_film_detail(SERPENTI_URL) is None
