"""Test del connettore Cinema Teatro Concordia su microdata reali registrati.

Fixture `concordia_home.html` scaricata **una volta sola** (2026-09-20) con lo
User-Agent del progetto: 2 film, 8 proiezioni, giorni 2026-09-20 → 2026-09-23.
La homepage marca ogni proiezione in microdata
`div[itemprop=startDate][content]` dentro uno `ScreeningEvent` con `itemtype` ad
apici singoli; il `Movie` è duplicato (antenato `w_film_cont` + `workPresented`).
Se il sito cambia markup la fixture va ri-registrata.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import responses

from scraper.config import CONCORDIA_URL, PROJECT_USER_AGENT
from scraper.connectors.cinema_teatro_concordia import CinemaTeatroConcordiaConnector
from scraper.models import Film

FIXTURES = Path(__file__).parent / "fixtures"

TODAY = "2026-09-20"
DATES = ["2026-09-20", "2026-09-21", "2026-09-22", "2026-09-23"]

INVITE = "THE INVITE – IL PIACERE È TUTTO..."
ULTIMO = "ULTIMO – TUTTO. LIVE A TOR VERGATA"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _by_title(films: list[Film], title: str) -> Film:
    return next(film for film in films if film.title == title)


@responses.activate
def test_extracts_movies_and_screenings_from_homepage_microdata():
    responses.add(responses.GET, CONCORDIA_URL, body=_load("concordia_home.html"), status=200)

    result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)

    assert result.errors == []
    assert {film.title for film in result.films} == {INVITE, ULTIMO}
    assert sum(len(showing.times) for film in result.films for showing in film.present_in) == 8


@responses.activate
def test_parses_start_date_from_content_attribute():
    responses.add(responses.GET, CONCORDIA_URL, body=_load("concordia_home.html"), status=200)

    result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)
    film = _by_title(result.films, INVITE)

    by_date = {showing.date: showing.times for showing in film.present_in}
    assert by_date["2026-09-20"] == ["18:30", "21:15"]
    assert by_date["2026-09-22"] == ["18:00"]


@responses.activate
def test_reads_screening_event_with_single_quoted_itemtype():
    responses.add(responses.GET, CONCORDIA_URL, body=_load("concordia_home.html"), status=200)

    # `itemtype='http://schema.org/ScreeningEvent'` (apici singoli) deve essere
    # riconosciuto come gli stessi eventi scritti con le virgolette doppie.
    result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)

    assert len(result.films) == 2
    assert result.errors == []


@responses.activate
def test_deduplicates_movie_appearing_both_ancestor_and_work_presented():
    responses.add(responses.GET, CONCORDIA_URL, body=_load("concordia_home.html"), status=200)

    result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)

    # Il `Movie` è ripetuto a livello `w_film_cont` e dentro `workPresented`:
    # deve restare un solo Film, con i metadati fusi una volta sola per URL.
    invite_films = [film for film in result.films if film.title == INVITE]
    assert len(invite_films) == 1
    film = invite_films[0]
    assert film.director == "Olivia Wilde"
    assert film.duration == "107 min"
    assert film.source_poster == (
        "https://www.cineconcordia.it/wp-content/uploads/2026/09/"
        "MV5BMjI0MzJjMjctNmQzZi00Y2U4LWEwZGItMmE3NDUzNzk1YzY3XkEyXkFqcGc@._V1_-360x530.jpg"
    )
    assert {showing.source_url for showing in film.present_in} == {
        "https://www.cineconcordia.it/films/the-invite-il-piacere-e-tutto-nostro/"
    }


@responses.activate
def test_maps_movie_duration_pt_to_minutes():
    responses.add(responses.GET, CONCORDIA_URL, body=_load("concordia_home.html"), status=200)

    result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)

    assert _by_title(result.films, INVITE).duration == "107 min"
    assert _by_title(result.films, ULTIMO).duration == "120 min"


@responses.activate
def test_filters_events_outside_requested_dates():
    responses.add(responses.GET, CONCORDIA_URL, body=_load("concordia_home.html"), status=200)

    result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=["2026-09-22"])

    assert {film.title for film in result.films} == {INVITE, ULTIMO}
    assert _by_title(result.films, INVITE).present_in[0].times == ["18:00"]
    assert _by_title(result.films, ULTIMO).present_in[0].times == ["20:00"]


@responses.activate
def test_decodes_html_entities_in_title():
    responses.add(responses.GET, CONCORDIA_URL, body=_load("concordia_home.html"), status=200)

    result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)

    titles = [film.title for film in result.films]
    assert all("&#" not in title for title in titles)
    assert INVITE in titles


@responses.activate
def test_tags_showings_with_cinema_name_and_slug():
    responses.add(responses.GET, CONCORDIA_URL, body=_load("concordia_home.html"), status=200)

    result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)

    showing = _by_title(result.films, INVITE).present_in[0]
    assert showing.cinema == "Cinema Teatro Concordia"
    assert showing.cinema_slug == "cinema-teatro-concordia"


@responses.activate
def test_sends_project_user_agent():
    responses.add(responses.GET, CONCORDIA_URL, body=_load("concordia_home.html"), status=200)

    CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)

    assert responses.calls[0].request.headers["User-Agent"] == PROJECT_USER_AGENT


@responses.activate
def test_returns_empty_list_when_no_screening_events():
    responses.add(responses.GET, CONCORDIA_URL, body="<html><body>vuoto</body></html>", status=200)

    result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)

    assert result.films == []
    assert result.errors == []


@responses.activate
def test_returns_error_result_when_homepage_unreachable():
    responses.add(responses.GET, CONCORDIA_URL, status=503)

    with mock.patch("scraper.http.time.sleep", return_value=None):
        result = CinemaTeatroConcordiaConnector().scrape(TODAY, dates=DATES)

    assert result.films == []
    assert len(result.errors) == 1
    assert result.errors[0].cinema == "Cinema Teatro Concordia"
    assert result.errors[0].phase == "scrape"
    assert result.errors[0].url == CONCORDIA_URL


def test_fetch_film_detail_is_not_needed_for_homepage_metadata():
    connector = CinemaTeatroConcordiaConnector()

    assert connector.fetch_film_detail("https://www.cineconcordia.it/films/the-invite/") is None
