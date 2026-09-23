"""Test dello script di manutenzione `app.maintenance.dedup_films`.

Solo SQLite in-memory (fixture `session` del conftest): nessun database reale,
nessun file toccato. I casi costruiscono la situazione vera del DB di sviluppo
(doppioni da titolo scritto diversamente + anno NULL) e ne verificano la fusione.
"""

from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.maintenance.dedup_films import run_maintenance
from app.models.cinema import Cinema
from app.models.film import Film
from app.models.showing import Showing

# Le due run reali del difetto: 17/09 (UCI, anno NULL) contro 20/09 (The Space, 2026).
OLD_RUN = datetime(2026, 9, 17, 12, 23)
NEW_RUN = datetime(2026, 9, 20, 16, 25)


@pytest.fixture
def uci(session) -> Cinema:
    """Un cinema di test su cui agganciare gli showings."""
    cinema = Cinema(slug="uci", name="UCI", city="Perugia", address="Via Roma 1", region="Umbria", lat=43.1, lon=12.4)
    session.add(cinema)
    session.commit()
    session.refresh(cinema)
    return cinema


def make_film(session, *, title, title_normalized, year=None, **meta) -> Film:
    """Crea un film con la chiave NATIVA che aveva nel DB (eventualmente legacy)."""
    film = Film(title=title, title_normalized=title_normalized, year=year, **meta)
    session.add(film)
    session.commit()
    session.refresh(film)
    return film


def make_showing(session, film, day, times, scraped_at, cinema) -> Showing:
    """Crea uno showing con lo `scraped_at` della run che lo ha prodotto."""
    showing = Showing(
        film_id=film.id,
        cinema_slug=cinema.slug,
        date=day,
        times=times,
        screen="2D",
        scraped_at=scraped_at,
    )
    session.add(showing)
    session.commit()
    session.refresh(showing)
    return showing


def snapshot_db(session) -> tuple:
    """Fotografia dell'intero DB: serve a dimostrare che il dry-run non scrive."""
    films = [
        (f.id, f.title, f.title_normalized, f.year, f.wikidata_id)
        for f in session.scalars(select(Film).order_by(Film.id))
    ]
    showings = [(s.id, s.film_id, s.date, s.times) for s in session.scalars(select(Showing).order_by(Showing.id))]
    return tuple(films), tuple(showings)


def test_dry_run_does_not_modify_the_database(session, uci):
    """Senza --apply il report si stampa e il database resta identico."""
    older = make_film(session, title="AMORI & INCANTESIMI 2", title_normalized="amori incantesimi 2")
    newer = make_film(
        session,
        title="Amori e incantesimi 2",
        title_normalized="amori e incantesimi 2",
        year=2026,
        wikidata_id="Q17052927",
    )
    make_showing(session, older, date(2026, 9, 22), '["16:15"]', OLD_RUN, uci)
    make_showing(session, newer, date(2026, 9, 22), '["16:00"]', NEW_RUN, uci)

    before = snapshot_db(session)
    report = run_maintenance(session, apply=False)

    assert "DRY-RUN" in report
    assert "-- Gruppi da fondere: 1" in report
    assert snapshot_db(session) == before


def test_merges_films_that_differ_only_by_ampersand_and_year(session, uci):
    """Caso reale (righe 40/52): chiave uguale dopo `&`→`e`, anno NULL contro 2026.

    Il superstite è la riga con più showings (regola 5.1); per le date in comune
    restano gli orari della run più recente (16:00), non quelli del 17/09.
    """
    older = make_film(session, title="AMORI & INCANTESIMI 2", title_normalized="amori incantesimi 2")
    newer = make_film(
        session,
        title="Amori e incantesimi 2",
        title_normalized="amori e incantesimi 2",
        year=2026,
        wikidata_id="Q17052927",
        director="Alessandro Genovese",
        poster_url="https://example.com/p.jpg",
    )
    for day in (date(2026, 9, 22), date(2026, 9, 23), date(2026, 9, 24), date(2026, 9, 25)):
        make_showing(session, older, day, '["16:15"]', OLD_RUN, uci)
    for day in (date(2026, 9, 22), date(2026, 9, 23)):
        make_showing(session, newer, day, '["16:00"]', NEW_RUN, uci)

    report = run_maintenance(session, apply=True)

    films = list(session.scalars(select(Film)))
    assert len(films) == 1
    survivor = films[0]
    assert survivor.id == older.id  # più showings in totale
    assert survivor.title == "AMORI & INCANTESIMI 2"  # il superstite tiene il proprio titolo
    assert survivor.year == 2026  # anno NULL adottato dal fuso
    assert survivor.wikidata_id == "Q17052927"  # metadati del fuso adottati dove mancavano
    assert survivor.director == "Alessandro Genovese"

    showings = list(session.scalars(select(Showing).order_by(Showing.date)))
    assert len(showings) == 4
    by_day = {s.date: s for s in showings}
    assert by_day[date(2026, 9, 22)].times == '["16:00"]'  # vince la run più recente
    assert by_day[date(2026, 9, 23)].times == '["16:00"]'
    assert by_day[date(2026, 9, 24)].times == '["16:15"]'  # date senza collisione: invariate
    assert by_day[date(2026, 9, 25)].times == '["16:15"]'
    assert all(s.film_id == survivor.id for s in showings)

    assert "showings ri-assegnati: 2" in report
    assert '["16:15"]' in report  # il report dice cosa ha scartato


def test_keeps_row_with_most_metadata_as_survivor(session):
    """A parità di showings e anno, sopravvive la riga con più metadati (regola 5.4)."""
    poorer = make_film(
        session,
        title="Il Padrino",
        title_normalized="il padrino",
        year=1972,
        poster_url="https://example.com/1.jpg",
    )
    richer = make_film(
        session,
        title="IL PADRINO",
        title_normalized="il padrino ",
        year=1972,
        poster_url="https://example.com/2.jpg",
        synopsis="La famiglia Corleone.",
        director="Francis Ford Coppola",
    )

    run_maintenance(session, apply=True)

    films = list(session.scalars(select(Film)))
    assert [f.id for f in films] == [richer.id]
    assert session.get(Film, poorer.id) is None  # la riga perdente sparisce
    assert films[0].poster_url == "https://example.com/2.jpg"


def test_does_not_merge_films_with_different_wikidata_ids(session):
    """Stessa chiave e stesso anno ma identità Wikidata diverse: nessuna invenzione."""
    first = make_film(
        session,
        title="Amori e incantesimi 2",
        title_normalized="amori e incantesimi 2",
        year=2026,
        wikidata_id="Q1",
    )
    second = make_film(
        session,
        title="AMORI & INCANTESIMI 2",
        title_normalized="amori incantesimi 2",
        year=2026,
        wikidata_id="Q2",
    )

    report = run_maintenance(session, apply=True)

    films = list(session.scalars(select(Film)))
    assert sorted(f.id for f in films) == sorted([first.id, second.id])
    assert "-- Da decidere (nessuna fusione automatica): 1" in report
    assert "wikidata_id in conflitto" in report
    assert "chiave NON ricalcolata" in report  # ricalcolarla violerebbe la UNIQUE
    survivor = next(f for f in films if f.id == second.id)
    assert survivor.title_normalized == "amori incantesimi 2"


def test_deletes_the_losing_film_and_its_showings(session, uci):
    """Il film perdente sparisce con lo showing che perde la collisione; il resto si ri-assegna."""
    winner = make_film(session, title="Amori e incantesimi 2", title_normalized="amori e incantesimi 2", year=2026)
    loser = make_film(session, title="AMORI & INCANTESIMI 2", title_normalized="amori incantesimi 2")
    make_showing(session, winner, date(2026, 9, 22), '["16:00"]', NEW_RUN, uci)
    make_showing(session, winner, date(2026, 9, 23), '["16:00"]', NEW_RUN, uci)
    make_showing(session, winner, date(2026, 9, 25), '["16:00"]', NEW_RUN, uci)
    loser_colliding = make_showing(session, loser, date(2026, 9, 22), '["16:15"]', OLD_RUN, uci)
    loser_free = make_showing(session, loser, date(2026, 9, 24), '["16:15"]', OLD_RUN, uci)

    run_maintenance(session, apply=True)

    assert session.get(Film, loser.id) is None
    assert session.get(Showing, loser_colliding.id) is None  # persa: la run recente aveva già 16:00
    assert session.get(Showing, loser_free.id).film_id == winner.id  # ri-assegnata al superstite
    assert list(session.scalars(select(Showing).where(Showing.film_id == loser.id))) == []
    assert len(list(session.scalars(select(Showing)))) == 4


def test_is_idempotent_on_second_run(session, uci):
    """Dopo --apply, un secondo dry-run non trova più niente da fare."""
    older = make_film(session, title="AMORI & INCANTESIMI 2", title_normalized="amori incantesimi 2")
    newer = make_film(
        session,
        title="Amori e incantesimi 2",
        title_normalized="amori e incantesimi 2",
        year=2026,
        wikidata_id="Q17052927",
    )
    make_showing(session, older, date(2026, 9, 22), '["16:15"]', OLD_RUN, uci)
    make_showing(session, newer, date(2026, 9, 22), '["16:00"]', NEW_RUN, uci)
    run_maintenance(session, apply=True)

    before = snapshot_db(session)
    report = run_maintenance(session, apply=False)

    assert "-- Gruppi da fondere: 0" in report
    assert "-- Chiavi da ricalcolare: 0" in report
    assert snapshot_db(session) == before


def test_reports_candidates_without_merging_them(session):
    """Titoli simili ma non identici: restano separati e compaiono fra i candidati."""
    godfather = make_film(session, title="Il Padrino", title_normalized="il padrino", year=1972)
    sequel = make_film(session, title="Il Padrino 2", title_normalized="il padrino 2", year=1974)

    report = run_maintenance(session, apply=True)

    films = list(session.scalars(select(Film)))
    assert sorted(f.id for f in films) == sorted([godfather.id, sequel.id])
    assert "-- Candidati per somiglianza (NON fusi: servono --merge): 1" in report
    assert "«Il Padrino»" in report and "«Il Padrino 2»" in report
    assert "distanza 2" in report


def test_reports_suffix_variant_as_candidate_without_merging_it(session):
    """La stessa opera con un suffisso di parole resta due righe, ma segnalata.

    È il caso reale «Talking Tom Heroes - Super amici» / «TALKING TOM HEROES SUPER
    AMICI AL CINEMA»: nessuna fusione automatica, il report propone --merge.
    """
    space = make_film(
        session,
        title="Talking Tom Heroes - Super amici",
        title_normalized="talking tom heroes super amici",
    )
    uci = make_film(
        session,
        title="TALKING TOM HEROES SUPER AMICI AL CINEMA",
        title_normalized="talking tom heroes super amici al cinema",
    )

    report = run_maintenance(session, apply=True)

    films = list(session.scalars(select(Film)))
    assert sorted(f.id for f in films) == sorted([space.id, uci.id])
    assert "-- Candidati per somiglianza (NON fusi: servono --merge): 1" in report
    assert "suffisso di parole" in report


def test_keeps_completely_different_titles_out_of_candidates(session):
    """Titoli italiani del tutto diversi per lo stesso film: nessuna regola li unisce.

    È il caso «CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO» / «Cars – 20esimo
    anniversario»: resta il lavoro a valle (merge cross-fonte), non è qui.
    """
    space = make_film(
        session,
        title="CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO",
        title_normalized="cars motori ruggenti 20mo anniversario",
    )
    uci = make_film(
        session,
        title="Cars – 20esimo anniversario",
        title_normalized="cars 20esimo anniversario",
        year=2006,
    )

    report = run_maintenance(session, apply=True)

    films = list(session.scalars(select(Film)))
    assert sorted(f.id for f in films) == sorted([space.id, uci.id])
    assert "-- Candidati per somiglianza (NON fusi: servono --merge): 0" in report


def test_merges_pair_approved_by_hand_even_with_different_titles(session):
    """`--merge A:B` fonde anche titoli diversissimi: l'approvazione è umana ed esplicita."""
    space = make_film(
        session,
        title="CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO",
        title_normalized="cars motori ruggenti 20mo anniversario",
    )
    uci_car = make_film(
        session,
        title="Cars – 20esimo anniversario",
        title_normalized="cars 20esimo anniversario",
        year=2026,
    )

    report = run_maintenance(session, apply=True, manual_pairs=[(space.id, uci_car.id)])

    films = list(session.scalars(select(Film)))
    assert len(films) == 1
    assert films[0].year == 2026  # anno adottato dal fuso
    assert "fusione esplicita --merge" in report
