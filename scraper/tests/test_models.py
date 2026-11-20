"""Test dei modelli e serializer: consolidamento showings e forma dei JSON di output."""

from __future__ import annotations

from datetime import datetime

from scraper.models import (
    CinemaError,
    Film,
    Showing,
    cinemas_to_json,
    films_to_json,
    output_to_json,
    showings_to_json,
)


def test_showing_creation():
    s = Showing(
        cinema="Test Cinema",
        cinema_slug="test-cinema",
        date="2026-06-12",
        times=["18:00", "20:30"],
        screen="Sala 1",
        source_url="https://example.com",
        language="ITA",
        session_attributes=["3D"],
    )
    assert s.cinema == "Test Cinema"
    assert s.times == ["18:00", "20:30"]
    assert s.screen == "Sala 1"


def test_film_creation():
    f = Film(
        title="Test Film",
        title_normalized="test film",
        present_in=[],
        poster="https://example.com/poster.jpg",
    )
    assert f.title == "Test Film"
    assert f.poster == "https://example.com/poster.jpg"


def test_output_to_json():
    film = Film(
        title="Test Film",
        title_normalized="test film",
        present_in=[
            Showing(
                cinema="Cinema A",
                cinema_slug="cinema-a",
                date="2026-06-12",
                times=["18:00"],
                screen="Sala 1",
            )
        ],
        poster="https://example.com/poster.jpg",
        description="A test film",
        genres=["Drama", "Thriller"],
    )
    error = CinemaError(
        cinema="Cinema B",
        timestamp="2026-06-12T10:00:00",
        exception="ConnectionError",
        phase="scrape",
        detail="Timeout",
    )
    output = output_to_json([film], [error], "TestCity")
    assert output["city"] == "TestCity"
    assert len(output["films"]) == 1
    assert len(output["errors"]) == 1
    assert output["films"][0]["title"] == "Test Film"
    assert output["films"][0]["present_in"][0]["cinema"] == "Cinema A"


def _sample_film() -> Film:
    return Film(
        title="Test Film",
        title_normalized="test film",
        present_in=[
            Showing(
                cinema="Cinema A",
                cinema_slug="cinema-a",
                date="2026-06-12",
                times=["18:00"],
                screen="Sala 1",
            )
        ],
    )


# I quattro file che il seed del backend legge: `generated_at` è il contratto che
# dice al backend quanto è vecchio il palinsesto che sta importando.
OUTPUT_PAYLOADS = {
    "cinemas.json": lambda: cinemas_to_json({"cinema-a": {"name": "Cinema A"}}),
    "films.json": lambda: films_to_json([_sample_film()]),
    "showings.json": lambda: showings_to_json([_sample_film()], "2026-06-12", "2026-06-18"),
    "movies.json": lambda: output_to_json([_sample_film()], [], "TestCity"),
}


def test_every_output_declares_run_timestamp_with_explicit_offset():
    # Il seed notturno rifiuta uno showings.json senza data della run: la
    # regressione deve fermarsi qui, nella CI dello scraper, non in produzione.
    for payload_name, build_payload in OUTPUT_PAYLOADS.items():
        payload = build_payload()

        generated_at = payload.get("generated_at")
        assert generated_at, f"{payload_name} non dichiara generated_at"

        try:
            parsed = datetime.fromisoformat(generated_at)
        except ValueError as exc:
            raise AssertionError(
                f"{payload_name}: generated_at non è un ISO 8601 valido ({generated_at}): {exc}"
            ) from exc

        assert parsed.utcoffset() is not None, (
            f"{payload_name}: generated_at senza offset esplicito ({generated_at}) — il fuso è Europe/Rome"
        )


def test_cinema_error_to_dict():
    e = CinemaError(
        cinema="Test",
        timestamp="2026-06-12T10:00:00",
        exception="ValueError",
        phase="parse",
        url="https://example.com",
        detail="Bad data",
    )
    d = e.to_dict()
    assert d["cinema"] == "Test"
    assert d["exception"] == "ValueError"
    assert d["url"] == "https://example.com"
