"""Test del connettore PostModernissimo su payload RSC e HTML registrati."""

from __future__ import annotations

import json

import responses

from scraper.config import POSTMOD_CINEMA_URL
from scraper.connectors.postmodernissimo import PostModernissimoConnector


def _build_rsc_push(movies: list[dict]) -> str:
    inner = json.dumps({"page": {"movies": movies}}, ensure_ascii=False, separators=(",", ":"))
    escaped = inner.replace("\\", "\\\\").replace('"', '\\"')
    return f'self.__next_f.push([1,"{escaped}"]);\n'


_EXTRA_PERMALINK = "https://www.postmodernissimo.com/extra/prince-of-broadway"
_FILMS_PERMALINK = "https://www.postmodernissimo.com/films/prince-of-broadway"


def _show(date: str, orario: str) -> dict:
    """Una proiezione nel formato del payload RSC (date YYYYMMDD, orario HH:MM)."""
    return {"date": date, "orario": orario, "opzioni": "off", "nota": None, "ticket": ""}


@responses.activate
def test_postmodernissimo_connector_scrape():
    rsc_push = _build_rsc_push(
        [
            {
                "id": 9999,
                "title": "Test Film",
                "slug": "test-film",
                "permalink": "https://www.postmodernissimo.com/films/test-film",
                "content": "A test film description.",
                "details": {
                    "regia": "Test Director",
                    "genere": "Commedia, Drammatico",
                    "durata": "120",
                    "nazione": "Italia",
                    "anno": "2026",
                    "youtube_cover": {"url": "https://example.com/poster.jpg"},
                },
                "programmazione": {
                    "spazio_prog": "postmod",
                    "shows": [
                        {"date": "20260612", "orario": "19:00", "opzioni": "off", "nota": None, "ticket": ""},
                        {"date": "20260612", "orario": "21:30", "opzioni": "off", "nota": None, "ticket": ""},
                        {"date": "20260613", "orario": "19:00", "opzioni": "off", "nota": None, "ticket": ""},
                    ],
                },
            }
        ]
    )

    html_content = f"""
    <html>
    <body>
    <script>{rsc_push}</script>
    <ul class="movie-container">
        <li class="movie-item">
            <a href="/films/test-film">
                <h2>Test Film</h2>
                <p class="text-sm">Test Director</p>
                <img src="https://example.com/poster.jpg">
            </a>
        </li>
    </ul>
    </body>
    </html>
    """
    responses.add(
        responses.GET,
        POSTMOD_CINEMA_URL,
        body=html_content,
        status=200,
    )

    connector = PostModernissimoConnector()
    result = connector.scrape("2026-06-12", dates=["2026-06-12", "2026-06-13"])

    assert len(result.films) >= 1
    film = result.films[0]
    assert film.title == "Test Film"
    assert film.director == "Test Director"
    assert film.duration == "120"
    assert "Commedia" in film.genres
    assert len(film.present_in) == 2
    assert film.present_in[0].date == "2026-06-12"
    assert film.present_in[0].times == ["19:00", "21:30"]
    assert film.present_in[1].date == "2026-06-13"
    assert film.present_in[1].times == ["19:00"]


@responses.activate
def test_postmodernissimo_skips_weekend_only():
    rsc_push = _build_rsc_push(
        [
            {
                "id": 9998,
                "title": "Weekend Film",
                "slug": "weekend-film",
                "permalink": "https://www.postmodernissimo.com/films/weekend-film",
                "content": "",
                "details": {"regia": None, "genere": "", "durata": None},
                "programmazione": {
                    "spazio_prog": "postmod",
                    "shows": [
                        {"date": "20260620", "orario": "20:00", "opzioni": "off", "nota": None, "ticket": ""},
                        {"date": "20260621", "orario": "20:00", "opzioni": "off", "nota": None, "ticket": ""},
                    ],
                },
            }
        ]
    )

    html_content = f"""
    <html><body>
    <script>{rsc_push}</script>
    </body></html>
    """
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=html_content, status=200)

    connector = PostModernissimoConnector()
    result = connector.scrape(
        "2026-06-12",
        dates=["2026-06-12", "2026-06-13", "2026-06-14"],
    )

    assert len(result.films) == 0


@responses.activate
def test_postmodernissimo_director_cleaned():
    rsc_push = _build_rsc_push(
        [
            {
                "id": 9997,
                "title": "Clean Film",
                "slug": "clean-film",
                "permalink": "https://www.postmodernissimo.com/films/clean-film",
                "content": "",
                "details": {"regia": "  (  John Doe  )  ", "genere": "", "durata": None},
                "programmazione": {
                    "spazio_prog": "postmod",
                    "shows": [
                        {"date": "20260612", "orario": "18:00", "opzioni": "off", "nota": None, "ticket": ""},
                    ],
                },
            }
        ]
    )

    html_content = f"<html><body><script>{rsc_push}</script></body></html>"
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=html_content, status=200)

    connector = PostModernissimoConnector()
    result = connector.scrape("2026-06-12", dates=["2026-06-12"])

    assert len(result.films) == 1
    assert result.films[0].director == "John Doe"


@responses.activate
def test_extra_permalink_resolves_to_film_page_and_merges_shows():
    # Arrange: il record /extra/ porta il film annidato sotto `movie`, più un record
    # /films/ separato dello stesso film con date diverse.
    extra_record = {
        "id": 41200,
        "title": "Prince of Broadway",
        "slug": "prince-of-broadway",
        "permalink": _EXTRA_PERMALINK,
        "content": "Proiezione unica in lingua originale.",
        "details": {"regia": "Sean Baker", "genere": "Commedia, Drammatico", "durata": "98"},
        "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261123", "21:30")]},
        "movie": {
            "id": 30500,
            "title": "Prince of Broadway",
            "slug": "prince-of-broadway",
            "permalink": _FILMS_PERMALINK,
            "content": "Sinossi del film.",
            "details": {"regia": "Sean Baker", "genere": "Commedia, Drammatico", "durata": "98"},
            "programmazione": {"spazio_prog": "postmod", "shows": []},
        },
    }
    films_record = {
        "id": 30500,
        "title": "Prince of Broadway",
        "slug": "prince-of-broadway",
        "permalink": _FILMS_PERMALINK,
        "content": "Sinossi del film dalla pagina del film.",
        "details": {"regia": "Sean Baker", "genere": "Commedia, Drammatico", "durata": "98"},
        "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261124", "21:00")]},
    }
    rsc_push = _build_rsc_push([extra_record, films_record])
    homepage_html = f"<html><body><script>{rsc_push}</script></body></html>"
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=homepage_html, status=200)
    # Pagina del film: senza payload RSC di show, la riconciliazione tiene i dati homepage.
    responses.add(
        responses.GET,
        _FILMS_PERMALINK,
        body="<html><body><article><p>Sinossi dalla pagina del film.</p></article></body></html>",
        status=200,
    )

    # Act
    connector = PostModernissimoConnector()
    result = connector.scrape("2026-11-23", dates=["2026-11-23", "2026-11-24"])

    # Assert: una sola voce di film, link sulla pagina /films/ e orari di entrambi i record.
    assert len(result.films) == 1
    film = result.films[0]
    assert film.title == "Prince of Broadway"
    assert [s.date for s in film.present_in] == ["2026-11-23", "2026-11-24"]
    assert film.present_in[0].times == ["21:30"]
    assert film.present_in[1].times == ["21:00"]
    assert {s.source_url for s in film.present_in} == {_FILMS_PERMALINK}
    assert result.errors == []


@responses.activate
def test_extra_record_with_long_synopsis_before_nested_movie_resolves_film_page():
    # Arrange: la voce /extra/ porta ~4000 caratteri di sinossi prima dell'oggetto
    # `movie` annidato, che è l'unico a portare il permalink /films/.
    long_synopsis = "Sinossi intera del film. " * 150
    extra_record = {
        "id": 41204,
        "title": "Prince of Broadway",
        "slug": "prince-of-broadway",
        "permalink": _EXTRA_PERMALINK,
        "content": long_synopsis,
        "details": {"regia": "Sean Baker", "genere": "Commedia, Drammatico", "durata": "98"},
        "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261123", "21:30")]},
        "movie": {
            # `permalink` prima degli altri campi: un oggetto annidato in quest'ordine non
            # combacia col regex dei record, quindi il link può arrivare solo dalla
            # risoluzione dentro il record, che senza confine di record si fermava a 3000.
            "permalink": _FILMS_PERMALINK,
            "id": 30500,
            "title": "Prince of Broadway",
            "slug": "prince-of-broadway",
            "content": "Sinossi del film.",
            "details": {"regia": "Sean Baker", "genere": "Commedia, Drammatico", "durata": "98"},
            "programmazione": {"spazio_prog": "postmod", "shows": []},
        },
    }
    rsc_push = _build_rsc_push([extra_record])
    homepage_html = f"<html><body><script>{rsc_push}</script></body></html>"
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=homepage_html, status=200)
    # Pagina del film: senza payload RSC di show, la riconciliazione tiene i dati homepage.
    responses.add(
        responses.GET,
        _FILMS_PERMALINK,
        body="<html><body></body></html>",
        status=200,
    )

    # Act
    connector = PostModernissimoConnector()
    result = connector.scrape("2026-11-23", dates=["2026-11-23"])

    # Assert: la pagina film viene risolta nonostante la sinossi lunga, e interrogata.
    assert len(result.films) == 1
    film = result.films[0]
    assert [s.date for s in film.present_in] == ["2026-11-23"]
    assert film.present_in[0].times == ["21:30"]
    assert {s.source_url for s in film.present_in} == {_FILMS_PERMALINK}
    requested = [call.request.url or "" for call in responses.calls]
    assert _FILMS_PERMALINK in requested, requested
    assert result.errors == []


@responses.activate
def test_films_record_before_extra_record_yields_single_film_with_full_description():
    # Arrange: il record /films/ precede quello /extra/ dello stesso slug, e i due
    # portano varianti di `content` di lunghezza diversa.
    full_synopsis = "Sinossi intera dalla pagina del film. " * 10
    films_record = {
        "id": 30500,
        "title": "Prince of Broadway",
        "slug": "prince-of-broadway",
        "permalink": _FILMS_PERMALINK,
        "content": full_synopsis,
        "details": {"regia": "Sean Baker", "genere": "Commedia, Drammatico", "durata": "98"},
        "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261124", "21:00")]},
    }
    extra_record = {
        "id": 41205,
        "title": "Prince of Broadway",
        "slug": "prince-of-broadway",
        "permalink": _EXTRA_PERMALINK,
        "content": "Proiezione unica in lingua originale.",
        "details": {"regia": "Sean Baker", "genere": "Commedia, Drammatico", "durata": "98"},
        "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261123", "21:30")]},
    }
    rsc_push = _build_rsc_push([films_record, extra_record])
    homepage_html = f"<html><body><script>{rsc_push}</script></body></html>"
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=homepage_html, status=200)
    # Pagina del film: senza payload RSC di show, la riconciliazione tiene i dati homepage.
    responses.add(
        responses.GET,
        _FILMS_PERMALINK,
        body="<html><body></body></html>",
        status=200,
    )

    # Act
    connector = PostModernissimoConnector()
    result = connector.scrape("2026-11-23", dates=["2026-11-23", "2026-11-24"])

    # Assert: una sola voce, date di entrambi i record e sinossi più completa conservata.
    assert len(result.films) == 1
    film = result.films[0]
    assert film.title == "Prince of Broadway"
    assert [s.date for s in film.present_in] == ["2026-11-23", "2026-11-24"]
    assert film.present_in[0].times == ["21:30"]
    assert film.present_in[1].times == ["21:00"]
    assert {s.source_url for s in film.present_in} == {_FILMS_PERMALINK}
    assert film.description == full_synopsis
    assert result.errors == []


@responses.activate
def test_unresolved_extra_record_takes_permalink_from_later_film_record():
    # Arrange: la voce /extra/ arriva prima e non porta la pagina film (il suo unico
    # permalink è la route morta `/extra/`, nessun `movie` annidato): la risoluzione
    # torna None e il permalink buono del record /films/ successivo deve completare il
    # record nato dalla fusione, non essere scartato.
    # Il `content` lungo serve a mostrare che la lunghezza del record non entra nella
    # risoluzione.
    extra_record = {
        "id": 41202,
        "title": "Prince of Broadway",
        "slug": "prince-of-broadway",
        "permalink": _EXTRA_PERMALINK,
        "content": "X" * 4000,
        "details": {"regia": "Sean Baker", "genere": "Commedia, Drammatico", "durata": "98"},
        "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261123", "21:30")]},
    }
    films_record = {
        "id": 30500,
        "title": "Prince of Broadway",
        "slug": "prince-of-broadway",
        "permalink": _FILMS_PERMALINK,
        "content": "",
        "details": {"regia": "Sean Baker", "genere": "Commedia, Drammatico", "durata": "98"},
        "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261124", "21:00")]},
    }
    rsc_push = _build_rsc_push([extra_record, films_record])
    homepage_html = f"<html><body><script>{rsc_push}</script></body></html>"
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=homepage_html, status=200)
    # Pagina del film: con il permalink completato la riconciliazione la interroga.
    responses.add(
        responses.GET,
        _FILMS_PERMALINK,
        body="<html><body></body></html>",
        status=200,
    )

    # Act
    connector = PostModernissimoConnector()
    result = connector.scrape("2026-11-23", dates=["2026-11-23", "2026-11-24"])

    # Assert: una sola voce, date di entrambi i record, link della pagina film su tutte.
    assert len(result.films) == 1
    film = result.films[0]
    assert [s.date for s in film.present_in] == ["2026-11-23", "2026-11-24"]
    assert {s.source_url for s in film.present_in} == {_FILMS_PERMALINK}
    assert result.errors == []


@responses.activate
def test_extra_record_without_film_page_keeps_shows_without_source_url():
    # Arrange: nessun permalink /films/ in tutta la pagina, quindi niente da risolvere.
    rsc_push = _build_rsc_push(
        [
            {
                "id": 41201,
                "title": "Documentario Senza Pagina",
                "slug": "documentario-senza-pagina",
                "permalink": "https://www.postmodernissimo.com/extra/documentario-senza-pagina",
                "content": "",
                "details": {"regia": "Regista Inventato", "genere": "Documentario", "durata": "85"},
                "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261123", "19:00")]},
            }
        ]
    )
    homepage_html = f"<html><body><script>{rsc_push}</script></body></html>"
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=homepage_html, status=200)
    # Sentinella: se il connettore chiedesse la route morta la richiesta finirebbe in
    # responses.calls (invece di sollevare) e l'asserzione finale la vedrebbe.
    responses.add(
        responses.GET,
        "https://www.postmodernissimo.com/extra/documentario-senza-pagina",
        body="<html><body></body></html>",
        status=200,
    )

    # Act
    connector = PostModernissimoConnector()
    result = connector.scrape("2026-11-23", dates=["2026-11-23"])

    # Assert
    assert len(result.films) == 1
    film = result.films[0]
    assert film.title == "Documentario Senza Pagina"
    assert film.present_in[0].date == "2026-11-23"
    assert film.present_in[0].times == ["19:00"]
    assert film.present_in[0].source_url is None
    # Negli stub di responses `request.url` è `str | None`: un'url assente non può
    # contenere la route morta, quindi diventa stringa vuota.
    requested = [call.request.url or "" for call in responses.calls]
    assert all("/extra/" not in url for url in requested), requested


@responses.activate
def test_event_permalink_is_still_discarded():
    # Arrange: record sotto /eventi/, con un titolo senza parole-spia da evento.
    rsc_push = _build_rsc_push(
        [
            {
                "id": 41202,
                "title": "Notte Horror",
                "slug": "notte-horror",
                "permalink": "https://www.postmodernissimo.com/eventi/notte-horror",
                "content": "",
                "details": {"regia": None, "genere": "", "durata": None},
                "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261123", "23:00")]},
            }
        ]
    )
    homepage_html = f"<html><body><script>{rsc_push}</script></body></html>"
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=homepage_html, status=200)

    # Act
    connector = PostModernissimoConnector()
    result = connector.scrape("2026-11-23", dates=["2026-11-23"])

    # Assert
    assert result.films == []


@responses.activate
def test_extra_record_with_mismatched_film_slug_stays_unresolved():
    # Arrange: il permalink /films/ vicino è di un altro film, quindi non vale la risoluzione.
    rsc_push = _build_rsc_push(
        [
            {
                "id": 41203,
                "title": "Prince of Broadway",
                "slug": "prince-of-broadway",
                "permalink": _EXTRA_PERMALINK,
                "content": "Proiezione unica.",
                "details": {"regia": "Sean Baker", "genere": "Commedia", "durata": "98"},
                "programmazione": {"spazio_prog": "postmod", "shows": [_show("20261123", "18:00")]},
                "movie": {
                    "id": 30999,
                    "title": "Un Altro Film",
                    "slug": "un-altro-film",
                    "permalink": "https://www.postmodernissimo.com/films/un-altro-film",
                    "content": "",
                    "details": {},
                    "programmazione": {"spazio_prog": "postmod", "shows": []},
                },
            }
        ]
    )
    homepage_html = f"<html><body><script>{rsc_push}</script></body></html>"
    responses.add(responses.GET, POSTMOD_CINEMA_URL, body=homepage_html, status=200)

    # Act
    connector = PostModernissimoConnector()
    result = connector.scrape("2026-11-23", dates=["2026-11-23"])

    # Assert: gli orari restano, il link no.
    assert len(result.films) == 1
    film = result.films[0]
    assert film.present_in[0].times == ["18:00"]
    assert film.present_in[0].source_url is None
