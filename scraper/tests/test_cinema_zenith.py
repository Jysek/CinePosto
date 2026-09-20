"""Test del connettore Cinema Zenith su pagine reali registrate e risposte HTTP mockate."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import responses

from scraper.config import CINEMA_ZENITH_URL, CINEMA_ZENITH_WEEK_URL, PROJECT_USER_AGENT
from scraper.connectors.cinema_zenith import CinemaZenithConnector
from scraper.models import Film

FIXTURES = Path(__file__).parent / "fixtures"

TODAY = "2026-09-20"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _by_title(films: list[Film], title: str) -> Film:
    return next(film for film in films if film.title == title)


@responses.activate
def test_extracts_movie_and_screening_events_from_jsonld_graph():
    responses.add(responses.GET, CINEMA_ZENITH_URL, body=_load("zenith_home.html"), status=200)

    result = CinemaZenithConnector().scrape(TODAY, dates=[TODAY])

    assert len(result.errors) == 0
    assert {film.title for film in result.films} == {"The Invite – Il piacere è tutto nostro", "Dov’è la Fiesta?"}
    # Con eventi in homepage non deve servire la pagina settimana.
    assert len(responses.calls) == 1


@responses.activate
def test_maps_work_presented_id_to_movie_metadata():
    responses.add(responses.GET, CINEMA_ZENITH_URL, body=_load("zenith_home.html"), status=200)

    result = CinemaZenithConnector().scrape(TODAY, dates=[TODAY])

    film = _by_title(result.films, "Dov’è la Fiesta?")
    assert film.director == "Niccolò Gentili"
    assert film.duration == "102 min"
    assert film.source_poster is not None


@responses.activate
def test_parses_iso_duration_to_minutes():
    responses.add(responses.GET, CINEMA_ZENITH_URL, body=_load("zenith_home.html"), status=200)

    result = CinemaZenithConnector().scrape(TODAY, dates=[TODAY])

    assert _by_title(result.films, "The Invite – Il piacere è tutto nostro").duration == "107 min"


@responses.activate
def test_tags_showings_with_cinema_name_and_slug():
    responses.add(responses.GET, CINEMA_ZENITH_URL, body=_load("zenith_home.html"), status=200)

    result = CinemaZenithConnector().scrape(TODAY, dates=[TODAY])

    showing = _by_title(result.films, "Dov’è la Fiesta?").present_in[0]
    assert showing.cinema == "Cinema Zenith"
    assert showing.cinema_slug == "cinema-zenith"


@responses.activate
def test_sends_project_user_agent():
    responses.add(responses.GET, CINEMA_ZENITH_URL, body=_load("zenith_home.html"), status=200)

    CinemaZenithConnector().scrape(TODAY, dates=[TODAY])

    assert responses.calls[0].request.headers["User-Agent"] == PROJECT_USER_AGENT


@responses.activate
def test_filters_events_outside_requested_dates():
    responses.add(responses.GET, CINEMA_ZENITH_URL, body=_load("zenith_home.html"), status=200)

    result = CinemaZenithConnector().scrape(TODAY, dates=["2026-09-25"])

    assert [film.title for film in result.films] == ["A Fox Under a Pink Moon"]
    assert result.films[0].present_in[0].times == ["21:00"]


@responses.activate
def test_decodes_html_entities_in_title():
    html = (
        '<script type="application/ld+json">'
        '{"@graph":['
        '{"@type":"Movie","@id":"https://cinemazenith.it/film/paw-patrol/","name":"Paw Patrol &#8211; Missione"},'
        '{"@type":"ScreeningEvent","name":"Paw Patrol &#8211; Missione",'
        '"workPresented":{"@type":"Movie","@id":"https://cinemazenith.it/film/paw-patrol/"},'
        '"startDate":"2026-09-20T15:00:00+02:00"}'
        "]}"
        "</script>"
    )
    responses.add(responses.GET, CINEMA_ZENITH_URL, body=html, status=200)

    result = CinemaZenithConnector().scrape(TODAY, dates=[TODAY])

    assert result.films[0].title == "Paw Patrol – Missione"


@responses.activate
def test_falls_back_to_week_page_when_homepage_has_no_events():
    responses.add(responses.GET, CINEMA_ZENITH_URL, body="<html><body>vuoto</body></html>", status=200)
    responses.add(responses.GET, CINEMA_ZENITH_WEEK_URL, body=_load("zenith_week.html"), status=200)

    result = CinemaZenithConnector().scrape(TODAY, dates=["2026-09-26"])

    assert {film.title for film in result.films} == {
        "Endless Cookie",
        "Como tú me ves",
        "PerSo Short Award",
        "A Fox Under a Pink Moon",
    }
    assert [call.request.url for call in responses.calls] == [CINEMA_ZENITH_URL, CINEMA_ZENITH_WEEK_URL]


@responses.activate
def test_returns_empty_list_when_page_has_no_screening_events():
    responses.add(responses.GET, CINEMA_ZENITH_URL, body="<html><body>vuoto</body></html>", status=200)
    responses.add(responses.GET, CINEMA_ZENITH_WEEK_URL, body="<html><body>vuoto</body></html>", status=200)

    result = CinemaZenithConnector().scrape(TODAY, dates=[TODAY])

    assert result.films == []
    assert result.errors == []


@responses.activate
def test_returns_error_result_when_both_sources_fail():
    responses.add(responses.GET, CINEMA_ZENITH_URL, body="<html><body>vuoto</body></html>", status=200)
    responses.add(responses.GET, CINEMA_ZENITH_WEEK_URL, status=503)

    with mock.patch("scraper.http.time.sleep", return_value=None):
        result = CinemaZenithConnector().scrape(TODAY, dates=[TODAY])

    assert result.films == []
    assert len(result.errors) == 1
    assert result.errors[0].cinema == "Cinema Zenith"
    assert result.errors[0].phase == "scrape"
    assert result.errors[0].url == CINEMA_ZENITH_WEEK_URL
