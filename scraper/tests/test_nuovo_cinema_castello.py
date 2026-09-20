"""Test del connettore Nuovo Cinema Castello su pagina reale registrata e HTTP mockato.

Fixture `castello_home.html` scaricata **una volta sola** (2026-09-20) con lo
User-Agent del progetto: 5 film, 18 proiezioni, giorni 2026-09-20 → 2026-09-23.
Se il sito cambia markup va ri-registrata.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import responses

from scraper.config import NUOVO_CASTELLO_URL, PROJECT_USER_AGENT
from scraper.connectors.nuovo_cinema_castello import NuovoCinemaCastelloConnector
from scraper.models import Film

FIXTURES = Path(__file__).parent / "fixtures"

TODAY = "2026-09-20"
DATES = ["2026-09-20", "2026-09-21", "2026-09-22", "2026-09-23"]


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _by_title(films: list[Film], title: str) -> Film:
    return next(film for film in films if film.title == title)


@responses.activate
def test_extracts_five_movies_from_jsonld_graph():
    responses.add(responses.GET, NUOVO_CASTELLO_URL, body=_load("castello_home.html"), status=200)

    result = NuovoCinemaCastelloConnector().scrape(TODAY, dates=DATES)

    assert result.errors == []
    assert {film.title for film in result.films} == {
        "Paw Patrol – Missione Dinosauri",
        "Serpenti",
        "The Echo Chamber",
        "Resident Evil",
        "Palestina 36 – Quando tutto ebbe inizio",
    }
    assert sum(len(showing.times) for film in result.films for showing in film.present_in) == 18


@responses.activate
def test_decodes_numeric_html_entities_in_title():
    responses.add(responses.GET, NUOVO_CASTELLO_URL, body=_load("castello_home.html"), status=200)

    result = NuovoCinemaCastelloConnector().scrape(TODAY, dates=DATES)

    titles = [film.title for film in result.films]
    assert "Paw Patrol – Missione Dinosauri" in titles
    assert all("&#" not in title for title in titles)


@responses.activate
def test_maps_screening_to_movie_via_work_presented_id():
    responses.add(responses.GET, NUOVO_CASTELLO_URL, body=_load("castello_home.html"), status=200)

    result = NuovoCinemaCastelloConnector().scrape(TODAY, dates=DATES)

    film = _by_title(result.films, "Paw Patrol – Missione Dinosauri")
    # Director/durata/poster vivono solo sul nodo `Movie`, raggiunto via `workPresented.@id`.
    assert film.director == "Cal Brunker"
    assert film.duration == "82 min"
    assert film.source_poster == (
        "https://www.nuovocinemacastello.it/wp-content/uploads/2026/09/Paw-locandinapg1.jpg"
    )
    assert film.present_in[0].source_url == "https://www.nuovocinemacastello.it/film/paw-patrol-missione-dinosauri/"


@responses.activate
def test_filters_events_outside_requested_dates():
    responses.add(responses.GET, NUOVO_CASTELLO_URL, body=_load("castello_home.html"), status=200)

    result = NuovoCinemaCastelloConnector().scrape(TODAY, dates=["2026-09-23"])

    assert {film.title for film in result.films} == {
        "Serpenti",
        "The Echo Chamber",
        "Palestina 36 – Quando tutto ebbe inizio",
    }
    assert _by_title(result.films, "Serpenti").present_in[0].times == ["18:15", "21:00"]


@responses.activate
def test_tags_showings_with_cinema_name_and_slug():
    responses.add(responses.GET, NUOVO_CASTELLO_URL, body=_load("castello_home.html"), status=200)

    result = NuovoCinemaCastelloConnector().scrape(TODAY, dates=DATES)

    showing = _by_title(result.films, "Serpenti").present_in[0]
    assert showing.cinema == "Nuovo Cinema Castello"
    assert showing.cinema_slug == "nuovo-cinema-castello"


@responses.activate
def test_sends_project_user_agent():
    responses.add(responses.GET, NUOVO_CASTELLO_URL, body=_load("castello_home.html"), status=200)

    NuovoCinemaCastelloConnector().scrape(TODAY, dates=DATES)

    assert responses.calls[0].request.headers["User-Agent"] == PROJECT_USER_AGENT


@responses.activate
def test_returns_error_result_when_homepage_unreachable():
    responses.add(responses.GET, NUOVO_CASTELLO_URL, status=503)

    with mock.patch("scraper.http.time.sleep", return_value=None):
        result = NuovoCinemaCastelloConnector().scrape(TODAY, dates=DATES)

    assert result.films == []
    assert len(result.errors) == 1
    assert result.errors[0].cinema == "Nuovo Cinema Castello"
    assert result.errors[0].phase == "scrape"
    assert result.errors[0].url == NUOVO_CASTELLO_URL
