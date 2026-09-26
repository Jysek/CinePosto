"""Descrizioni PostModernissimo: sinossi intera, mai la meta description tronca.

Il connettore storico leggeva la descrizione dall'ultima fonte utile (meta
description del CMS, tagliata a ~100 caratteri a metà parola). Qui si fissano
l'ordine corretto delle fonti (payload RSC → primo paragrafo → meta) e la
regola di non-degrado fra run.
"""

from __future__ import annotations

import json
from unittest import mock

import responses

from scraper.config import POSTMOD_CINEMA_URL
from scraper.connectors.postmodernissimo import PostModernissimoConnector
from scraper.normalizer import pick_fuller_description

PERMALINK = "https://www.postmodernissimo.com/films/una-storia"
FULL_SYNOPSIS = "Una storia. Sinossi intera, scritta per esteso e senza tagli."
TRUNCATED_META = "Una storia. Sinossi che il CMS ha tagliato a metà par..."


def _rsc_push(movies: list[dict]) -> str:
    inner = json.dumps({"page": {"movies": movies}}, ensure_ascii=False, separators=(",", ":"))
    escaped = inner.replace("\\", "\\\\").replace('"', '\\"')
    return f'self.__next_f.push([1,"{escaped}"]);\n'


def _movie(content: str) -> dict:
    return {
        "id": 4242,
        "title": "Una storia",
        "slug": "una-storia",
        "permalink": PERMALINK,
        "content": content,
        "details": {"regia": "Anna Foglietta", "genere": "Drammatico", "durata": "100"},
        "programmazione": {
            "spazio_prog": "postmod",
            "shows": [
                {"date": "20260612", "orario": "19:00", "opzioni": "off", "nota": None, "ticket": ""},
            ],
        },
    }


def _homepage(content: str) -> str:
    return f"<html><body><script>{_rsc_push([_movie(content)])}</script></body></html>"


def _detail_html(body: str) -> str:
    return f"<html><head></head><body>{body}</body></html>"


@responses.activate
def test_prefers_full_synopsis_from_payload_over_meta_description():
    """Se il payload RSC porta la sinossi, si usa quella e non la meta tronca."""
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=_homepage(FULL_SYNOPSIS), status=200)
    responses.add(
        responses.GET,
        PERMALINK,
        body=_detail_html(f'<meta name="description" content="{TRUNCATED_META}">'),
        status=200,
    )

    result = PostModernissimoConnector().scrape("2026-06-12", dates=["2026-06-12"])

    assert len(result.films) == 1
    assert result.films[0].description == FULL_SYNOPSIS
    assert result.films[0].description != TRUNCATED_META


@responses.activate
def test_falls_back_to_detail_payload_synopsis_when_homepage_has_none():
    """Se la homepage non porta la sinossi, si usa quella del payload RSC del dettaglio."""
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=_homepage(""), status=200)
    detail = (
        f'<html><head><meta name="description" content="{TRUNCATED_META}"></head>'
        f"<body><script>{_rsc_push([_movie(FULL_SYNOPSIS)])}</script></body></html>"
    )
    responses.add(responses.GET, PERMALINK, body=detail, status=200)

    result = PostModernissimoConnector().scrape("2026-06-12", dates=["2026-06-12"])

    assert result.films[0].description == FULL_SYNOPSIS


@responses.activate
def test_falls_back_to_first_paragraph_when_payload_has_no_synopsis():
    """Senza sinossi nel payload vince il primo paragrafo, non la meta tronca."""
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=_homepage(""), status=200)
    responses.add(
        responses.GET,
        PERMALINK,
        body=_detail_html(
            f'<meta name="description" content="{TRUNCATED_META}"><article><p>{FULL_SYNOPSIS}</p></article>'
        ),
        status=200,
    )

    result = PostModernissimoConnector().scrape("2026-06-12", dates=["2026-06-12"])

    assert len(result.films) == 1
    assert result.films[0].description == FULL_SYNOPSIS


@responses.activate
def test_falls_back_to_meta_description_when_nothing_else():
    """Ultima spiaggia: senza paragrafo né payload, la meta viene comunque usata."""
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=_homepage(""), status=200)
    responses.add(
        responses.GET,
        PERMALINK,
        body=_detail_html(f'<meta name="description" content="{TRUNCATED_META}">'),
        status=200,
    )

    result = PostModernissimoConnector().scrape("2026-06-12", dates=["2026-06-12"])

    assert len(result.films) == 1
    assert result.films[0].description == TRUNCATED_META


@responses.activate
def test_scrape_never_raises_on_detail_fetch_failure():
    """Il dettaglio che fallisce non rompe la run: film presente ed errore registrato."""
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=_homepage(""), status=200)
    responses.add(responses.GET, PERMALINK, body="boom", status=500)

    with mock.patch("scraper.http.time.sleep"):
        result = PostModernissimoConnector().scrape("2026-06-12", dates=["2026-06-12"])

    assert len(result.films) == 1
    assert result.films[0].description is None
    assert any(error.phase == "detail" for error in result.errors)


def test_pick_fuller_description_prefers_text_without_ellipsis_cut():
    """Una sinossi intera batte sempre una tronca; a pari troncamento vince la lunga."""
    assert pick_fuller_description(TRUNCATED_META, FULL_SYNOPSIS) == FULL_SYNOPSIS
    assert pick_fuller_description(FULL_SYNOPSIS, TRUNCATED_META) == FULL_SYNOPSIS
    assert pick_fuller_description("corta...", "più lunga ma tronca...") == "più lunga ma tronca..."
    assert pick_fuller_description("breve", "descrizione molto più lunga e intera") == (
        "descrizione molto più lunga e intera"
    )
    assert pick_fuller_description(None, FULL_SYNOPSIS) == FULL_SYNOPSIS
    assert pick_fuller_description(FULL_SYNOPSIS, None) == FULL_SYNOPSIS


def test_extract_content_reads_the_field_even_when_details_come_first():
    """Il campo `content` non è ancorato all'ordine delle chiavi dell'oggetto."""
    connector = PostModernissimoConnector()
    payload = '{"id":1,"details":{"durata":null},"content":"Sinossi dopo i dettagli"}'

    assert connector._extract_content(payload, 0) == "Sinossi dopo i dettagli"


def test_extract_content_ignores_content_of_the_next_movie():
    """Un film senza content non si prende quello della voce successiva."""
    connector = PostModernissimoConnector()
    payload = '{"id":1,"title":"A"}{"id":2,"title":"B","content":"Di B"}'

    assert connector._extract_content(payload, 0) == ""
