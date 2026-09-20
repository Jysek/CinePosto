"""Test del connettore The Space: parsing su risposte registrate e venue per istanza.

Le fixture `thespace_terni_*_2026-09-19.json` sono un estratto (ripulito) delle
risposte reali del microservice per il venue Terni, registrate il 19/09/2026.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import responses

from scraper.config import (
    THE_SPACE_AUTH_URL,
    THE_SPACE_CINEMA_ID,
    THE_SPACE_CINEMA_NAME,
    THE_SPACE_CINEMA_SLUG,
    THE_SPACE_CINEMA_URL,
    THE_SPACE_CINEMAS_URL,
    THE_SPACE_TERNI_ID,
    THE_SPACE_TERNI_NAME,
    THE_SPACE_TERNI_SLUG,
    THE_SPACE_TERNI_URL,
    thespace_films_url,
)
from scraper.connectors.thespace import TheSpaceConnector, _extract_venues
from scraper.models import Film

FIXTURES = Path(__file__).parent / "fixtures"
TERNI_DATE = "2026-09-19"
CINEMAS_FIXTURE = "thespace_terni_cinemas_2026-09-19.json"
FILMS_FIXTURE = "thespace_terni_films_2026-09-19.json"


def _corciano() -> TheSpaceConnector:
    return TheSpaceConnector(THE_SPACE_CINEMA_ID, THE_SPACE_CINEMA_NAME, THE_SPACE_CINEMA_SLUG, THE_SPACE_CINEMA_URL)


def _terni() -> TheSpaceConnector:
    return TheSpaceConnector(THE_SPACE_TERNI_ID, THE_SPACE_TERNI_NAME, THE_SPACE_TERNI_SLUG, THE_SPACE_TERNI_URL)


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _requested_films_urls() -> list[str]:
    return [call.request.url for call in responses.calls if "/films" in call.request.url]


@pytest.fixture
def connector() -> TheSpaceConnector:
    """Connettore Corciano: i test di parsing non dipendono dal venue."""
    return _corciano()


# --- venue parametrizzato ---


def test_cinema_name_and_slug_come_from_instance():
    corciano, terni = _corciano(), _terni()
    assert corciano.cinema_name == "The Space Cinema Corciano"
    assert corciano.cinema_slug == "the-space-corciano"
    assert terni.cinema_name == "The Space Cinema Terni"
    assert terni.cinema_slug == "the-space-terni"


@responses.activate
def test_connector_uses_configured_cinema_id_in_films_url():
    responses.add(responses.POST, THE_SPACE_AUTH_URL, json={"result": {}}, status=200)
    responses.add(responses.GET, thespace_films_url(THE_SPACE_TERNI_ID), json={"result": []}, status=200)

    _terni().scrape(TERNI_DATE, dates=[TERNI_DATE])

    assert _requested_films_urls() == [
        f"{thespace_films_url(THE_SPACE_TERNI_ID)}?showingDate={TERNI_DATE}&includesSession=true&includeSessionAttributes=true"
    ]


@responses.activate
def test_resolves_venue_id_from_cinemas_endpoint_by_name():
    # Id in config volutamente sbagliato: l'elenco cinema deve correggerlo (Terni = 1006).
    responses.add(responses.POST, THE_SPACE_AUTH_URL, json={"result": {}}, status=200)
    responses.add(responses.GET, THE_SPACE_CINEMAS_URL, json=_fixture(CINEMAS_FIXTURE), status=200)
    responses.add(responses.GET, thespace_films_url(THE_SPACE_TERNI_ID), json={"result": []}, status=200)

    misconfigured = TheSpaceConnector(
        THE_SPACE_CINEMA_ID, THE_SPACE_TERNI_NAME, THE_SPACE_TERNI_SLUG, THE_SPACE_TERNI_URL
    )
    misconfigured.scrape(TERNI_DATE, dates=[TERNI_DATE])

    assert any(f"{thespace_films_url(THE_SPACE_TERNI_ID)}?" in url for url in _requested_films_urls())


@responses.activate
def test_resolves_corciano_venue_id_from_the_same_cinemas_endpoint():
    responses.add(responses.POST, THE_SPACE_AUTH_URL, json={"result": {}}, status=200)
    responses.add(responses.GET, THE_SPACE_CINEMAS_URL, json=_fixture(CINEMAS_FIXTURE), status=200)
    responses.add(responses.GET, thespace_films_url(THE_SPACE_CINEMA_ID), json={"result": []}, status=200)

    _corciano().scrape(TERNI_DATE, dates=[TERNI_DATE])

    assert any(f"{thespace_films_url(THE_SPACE_CINEMA_ID)}?" in url for url in _requested_films_urls())
    assert not any(f"{thespace_films_url(THE_SPACE_TERNI_ID)}?" in url for url in _requested_films_urls())


@responses.activate
def test_falls_back_to_hardcoded_venue_id_when_cinemas_endpoint_fails():
    responses.add(responses.POST, THE_SPACE_AUTH_URL, json={"result": {}}, status=200)
    # /showings/cinemas non è registrato: la risoluzione fallisce e vale l'id di config.
    responses.add(responses.GET, thespace_films_url(THE_SPACE_TERNI_ID), json={"result": []}, status=200)

    result = _terni().scrape(TERNI_DATE, dates=[TERNI_DATE])

    assert result.errors == []
    assert any(f"{thespace_films_url(THE_SPACE_TERNI_ID)}?" in url for url in _requested_films_urls())


@responses.activate
def test_scrape_labels_recorded_terni_sessions_with_terni_cinema():
    responses.add(responses.POST, THE_SPACE_AUTH_URL, json={"result": {}}, status=200)
    responses.add(responses.GET, THE_SPACE_CINEMAS_URL, json=_fixture(CINEMAS_FIXTURE), status=200)
    responses.add(responses.GET, thespace_films_url(THE_SPACE_TERNI_ID), json=_fixture(FILMS_FIXTURE), status=200)

    result = _terni().scrape(TERNI_DATE, dates=[TERNI_DATE])

    assert result.errors == []
    titles = {film.title for film in result.films}
    assert titles == {"Il Gladiatore", "Vermiglio"}
    showings = [showing for film in result.films for showing in film.present_in]
    assert showings
    for showing in showings:
        assert showing.cinema == THE_SPACE_TERNI_NAME
        assert showing.cinema_slug == THE_SPACE_TERNI_SLUG
        assert showing.date == TERNI_DATE
        assert showing.times
    gladiatore = next(film for film in result.films if film.title == "Il Gladiatore")
    assert sorted(showing.times[0] for showing in gladiatore.present_in) == ["17:30", "21:00"]
    assert {showing.screen for showing in gladiatore.present_in} == {"Sala 2", "Sala 5"}
    assert gladiatore.source_poster == "https://www.thespacecinema.it/media/films/il-gladiatore.jpg"


# --- estrazione venue da /showings/cinemas ---


def test_extract_venues_handles_letter_grouped_list_payload():
    venues = _extract_venues(_fixture(CINEMAS_FIXTURE))
    assert {venue["cinemaId"] for venue in venues} == {"1006", "1027"}


def test_extract_venues_handles_letter_grouped_dict_payload():
    payload = {"result": {"C": [{"cinemaId": "1027", "cinemaName": "Corciano"}]}}
    venues = _extract_venues(payload)
    assert [venue["cinemaId"] for venue in venues] == ["1027"]


# --- _parse_api_film ---


def test_parse_api_film_returns_film_with_all_fields(connector):
    data = {
        "filmTitle": "Test Film",
        "posterImageSrc": "https://example.com/poster.jpg",
        "synopsisShort": "A great film.",
        "runningTime": 120,
        "isDurationUnknown": False,
        "genres": ["Action", "Drama"],
        "director": "Test Director",
        "showingGroups": [
            {
                "date": "2026-06-24T00:00:00Z",
                "sessions": [{"startTime": "2026-06-24T20:00:00Z"}],
            }
        ],
    }
    film = connector._parse_api_film(data, "2026-06-24")
    assert isinstance(film, Film)
    assert film.title == "Test Film"
    assert film.description == "A great film."
    assert film.duration == "120 min"
    assert film.director == "Test Director"
    assert film.genres == ["Action", "Drama"]
    assert film.poster == "https://example.com/poster.jpg"
    assert film.source_poster == "https://example.com/poster.jpg"


def test_parse_api_film_returns_none_when_title_missing(connector):
    film = connector._parse_api_film({}, "2026-06-24")
    assert film is None


def test_parse_api_film_title_normalized_uses_normalize_title(connector):
    data = {
        "filmTitle": "Avengers: Endgame (2019)",
        "showingGroups": [
            {
                "date": "2026-06-24T00:00:00Z",
                "sessions": [{"startTime": "2026-06-24T18:00:00Z"}],
            }
        ],
    }
    film = connector._parse_api_film(data, "2026-06-24")
    # normalize_title strips the year suffix
    assert "2019" not in film.title_normalized


def test_parse_api_film_unknown_duration_is_none(connector):
    data = {
        "filmTitle": "Test",
        "runningTime": 90,
        "isDurationUnknown": True,
        "showingGroups": [
            {
                "date": "2026-06-24T00:00:00Z",
                "sessions": [{"startTime": "2026-06-24T18:00:00Z"}],
            }
        ],
    }
    film = connector._parse_api_film(data, "2026-06-24")
    assert film.duration is None


# --- _parse_api_showing_groups ---


def test_parse_showing_groups_extracts_time_from_iso_datetime(connector):
    data = {
        "showingGroups": [
            {
                "date": "2026-06-24T00:00:00Z",
                "sessions": [{"startTime": "2026-06-24T20:30:00Z"}],
            }
        ]
    }
    showings = connector._parse_api_showing_groups(data, "2026-06-24", "http://test")
    assert len(showings) == 1
    assert showings[0].times == ["20:30"]
    assert showings[0].date == "2026-06-24"


def test_parse_showing_groups_extracts_language_from_attributes(connector):
    data = {
        "showingGroups": [
            {
                "date": "2026-06-24T00:00:00Z",
                "sessions": [
                    {
                        "startTime": "2026-06-24T18:00:00Z",
                        "attributes": [
                            {"attributeType": "Language", "name": "ITA"},
                            {"attributeType": "Format", "name": "Dolby Atmos"},
                        ],
                    }
                ],
            }
        ]
    }
    showings = connector._parse_api_showing_groups(data, "2026-06-24", "http://test")
    assert showings[0].language == "ITA"
    assert "Dolby Atmos" in showings[0].session_attributes


def test_parse_showing_groups_skips_session_without_time(connector):
    data = {
        "showingGroups": [
            {
                "date": "2026-06-24T00:00:00Z",
                "sessions": [{"startTime": ""}],
            }
        ]
    }
    showings = connector._parse_api_showing_groups(data, "2026-06-24", "http://test")
    assert showings == []


def test_parse_showing_groups_empty_returns_empty_list(connector):
    data = {"showingGroups": []}
    showings = connector._parse_api_showing_groups(data, "2026-06-24", "http://test")
    assert showings == []


def test_parse_showing_groups_has_sessions_flag_ignored(connector):
    # hasSessions was dead code (always filtered by delta) — removed. Verify no side effect.
    data = {"showingGroups": [], "hasSessions": True}
    showings = connector._parse_api_showing_groups(data, "2026-06-24", "http://test")
    assert showings == []


def test_parse_showing_groups_skips_malformed_date(connector):
    data = {
        "showingGroups": [
            {
                "date": "not-a-date",
                "sessions": [{"startTime": "2026-06-24T18:00:00Z"}],
            }
        ]
    }
    showings = connector._parse_api_showing_groups(data, "2026-06-24", "http://test")
    assert showings == []
