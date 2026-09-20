"""Test dell'estrattore condiviso schema.org sulle tre forme di markup reali.

Fixture registrate una volta sola il 2026-09-20 con lo User-Agent del progetto:
`zenith_home.html` (JSON-LD `@graph`), `zenith_week.html` (microdata
`<time datetime>`), `concordia_home.html` (microdata `[itemprop=startDate][content]`).
Se i siti cambiano markup vanno ri-registrate.
"""

from __future__ import annotations

from pathlib import Path

from scraper.connectors.schema_org import (
    extract_jsonld_graph,
    extract_microdata_items,
    extract_screening_events,
    filter_films_to_dates,
)
from scraper.models import Film

FIXTURES = Path(__file__).parent / "fixtures"

ZENITH_HOME_URL = "https://cinemazenith.it/"
ZENITH_WEEK_URL = "https://cinemazenith.it/programmazione-settimana/"
CONCORDIA_HOME_URL = "https://www.cineconcordia.it/"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _by_title(films: list[Film], title: str) -> Film:
    return next(film for film in films if film.title == title)


# --- forma 1: JSON-LD @graph (Zenith homepage) ---


def test_extracts_all_movies_and_screenings_from_jsonld_graph():
    films = extract_screening_events(_load("zenith_home.html"), ZENITH_HOME_URL)

    assert len(films) == 7
    assert sum(len(showing.times) for film in films for showing in film.present_in) == 21


def test_maps_work_presented_id_to_movie_metadata():
    film = _by_title(extract_screening_events(_load("zenith_home.html"), ZENITH_HOME_URL), "Dov’è la Fiesta?")

    assert film.duration == "102 min"
    assert film.director == "Niccolò Gentili"
    assert film.source_poster == (
        "https://cinemazenith.it/wp-content/uploads/2026/09/DLEF_1080X1920-3piccolo.jpg"
    )
    assert film.present_in[0].source_url == "https://cinemazenith.it/film/dove-la-fiesta/"


def test_groups_multiple_times_by_date():
    film = _by_title(
        extract_screening_events(_load("zenith_home.html"), ZENITH_HOME_URL),
        "The Invite – Il piacere è tutto nostro",
    )

    by_date = {showing.date: showing.times for showing in film.present_in}
    assert by_date["2026-09-20"] == ["18:30", "21:15"]
    assert by_date["2026-09-23"] == ["18:30", "21:15"]


# --- forma 3: microdata <time datetime itemprop=startDate> (Zenith settimana) ---


def test_parses_start_date_from_time_datetime_attribute():
    films = extract_screening_events(_load("zenith_week.html"), ZENITH_WEEK_URL)
    film = _by_title(films, "Endless Cookie")

    assert len(films) == 7
    assert film.present_in[0].date == "2026-09-26"
    assert film.present_in[0].times == ["18:00"]


def test_uses_work_presented_string_as_title_with_ancestor_metadata():
    film = _by_title(
        extract_screening_events(_load("zenith_week.html"), ZENITH_WEEK_URL),
        "The Invite – Il piacere è tutto nostro",
    )

    # Il titolo è la stringa di workPresented; durata e regia arrivano dal Movie antenato.
    assert film.duration == "107 min"
    assert film.director == "Olivia Wilde"
    # La pagina settimana non espone poster né URL di dettaglio.
    assert film.source_poster is None
    assert film.present_in[0].source_url is None


# --- forma 2: microdata [itemprop=startDate][content] (Concordia homepage) ---


def test_parses_start_date_from_content_attribute():
    film = _by_title(
        extract_screening_events(_load("concordia_home.html"), CONCORDIA_HOME_URL),
        "THE INVITE – IL PIACERE È TUTTO...",
    )

    by_date = {showing.date: showing.times for showing in film.present_in}
    assert by_date["2026-09-20"] == ["18:30", "21:15"]
    assert by_date["2026-09-22"] == ["18:00"]


def test_reads_screening_event_with_single_quoted_itemtype():
    films = extract_screening_events(_load("concordia_home.html"), CONCORDIA_HOME_URL)

    assert len(films) == 2


def test_maps_microdata_movie_metadata_and_year():
    film = _by_title(
        extract_screening_events(_load("concordia_home.html"), CONCORDIA_HOME_URL),
        "ULTIMO – TUTTO. LIVE A TOR VERGATA",
    )

    assert film.duration == "120 min"
    assert film.director == "Giorgio Testi"
    assert film.year == 2026
    assert film.present_in[0].source_url == (
        "https://www.cineconcordia.it/films/ultimo-tutto-live-a-tor-vergata/"
    )


def test_decodes_html_entities_in_title():
    films = extract_screening_events(_load("concordia_home.html"), CONCORDIA_HOME_URL)
    titles = [film.title for film in films]

    assert all("&#8211;" not in title for title in titles)
    assert any("–" in title for title in titles)


# --- filtro per data (chiamato dal connettore) ---


def test_filter_films_to_dates_keeps_only_requested_dates():
    films = extract_screening_events(_load("zenith_home.html"), ZENITH_HOME_URL)

    filtered = filter_films_to_dates(films, ["2026-09-25"])

    assert [film.title for film in filtered] == ["A Fox Under a Pink Moon"]
    assert filtered[0].present_in[0].times == ["21:00"]


def test_filter_films_to_dates_drops_films_without_residual_showings():
    films = extract_screening_events(_load("zenith_home.html"), ZENITH_HOME_URL)

    # Il 24 settembre non c'è nessuno spettacolo in fixture.
    assert filter_films_to_dates(films, ["2026-09-24"]) == []


def test_filter_films_to_dates_does_not_filter_when_dates_none():
    films = extract_screening_events(_load("zenith_home.html"), ZENITH_HOME_URL)

    assert filter_films_to_dates(films, None) == films


# --- casi limite ---


def test_parses_iso_duration_to_minutes():
    html = """
    <div itemscope itemtype="http://schema.org/ScreeningEvent">
      <div itemprop="workPresented" itemscope itemtype="http://schema.org/Movie">
        <meta itemprop="name" content="Lungo"/>
        <meta itemprop="duration" content="PT1H49M"/>
      </div>
      <div itemprop="startDate" content="2026-09-20T20:00:00+02:00">20:00</div>
    </div>
    <div itemscope itemtype="http://schema.org/ScreeningEvent">
      <div itemprop="workPresented" itemscope itemtype="http://schema.org/Movie">
        <meta itemprop="name" content="Corto"/>
        <meta itemprop="duration" content="PT102M"/>
      </div>
      <div itemprop="startDate" content="2026-09-20T21:00:00+02:00">21:00</div>
    </div>
    """
    films = extract_screening_events(html, "https://example.org/")

    assert _by_title(films, "Lungo").duration == "109 min"
    assert _by_title(films, "Corto").duration == "102 min"


def test_falls_back_to_microdata_when_jsonld_is_malformed():
    html = """
    <html><head>
      <script type="application/ld+json">{ questo non è JSON valido </script>
    </head><body>
      <div itemscope itemtype="http://schema.org/ScreeningEvent">
        <meta itemprop="workPresented" content="Fallback Film">
        <time datetime="2026-09-20T20:00:00+02:00" itemprop="startDate">20:00</time>
      </div>
    </body></html>
    """
    films = extract_screening_events(html, "https://example.org/")

    assert [film.title for film in films] == ["Fallback Film"]
    assert films[0].present_in[0].date == "2026-09-20"


def test_returns_empty_list_when_page_has_no_screening_events():
    html = "<html><body><p>Nessuna programmazione disponibile</p></body></html>"

    assert extract_screening_events(html, "https://example.org/") == []


def test_skips_microdata_event_without_start_date():
    html = """
    <div itemscope itemtype="http://schema.org/ScreeningEvent">
      <meta itemprop="workPresented" content="Senza data">
    </div>
    """
    assert extract_screening_events(html, "https://example.org/") == []


def test_skips_jsonld_event_without_start_date():
    html = (
        '<script type="application/ld+json">'
        '{"@graph":[{"@type":"ScreeningEvent","name":"Senza data"}]}'
        "</script>"
    )
    assert extract_screening_events(html, "https://example.org/") == []


def test_extract_jsonld_graph_ignores_scripts_without_screening_event():
    html = '<script type="application/ld+json">{"@type":"WebSite","name":"Zenith"}</script>'

    assert extract_jsonld_graph(html) == []


def test_extract_microdata_items_returns_nested_screening_events():
    html = """
    <div itemscope itemtype="http://schema.org/Movie">
      <div itemscope itemtype="http://schema.org/ScreeningEvent">
        <time datetime="2026-09-20T20:00:00+02:00" itemprop="startDate">20:00</time>
      </div>
    </div>
    """

    items = extract_microdata_items(html, "ScreeningEvent")

    assert len(items) == 1
