"""Test della migrazione minima `removed_at` (ALTER TABLE idempotente).

Il DB contiene storico che va conservato: la migrazione aggiunge la colonna e
basta, non ricrea le tabelle. Questi test sono la prova che non si perde nulla.
"""

from sqlalchemy import create_engine

from app.maintenance.migrate_removed_at import ensure_removed_at_columns, ensure_removed_at_columns_on_engine


def _legacy_engine():
    """Engine con lo schema DI PRIMA della migrazione (niente `removed_at`)."""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE films (id INTEGER PRIMARY KEY, title TEXT)")
        conn.exec_driver_sql("CREATE TABLE showings (id INTEGER PRIMARY KEY, film_id INTEGER)")
    return engine


def _columns(conn, table: str) -> set[str]:
    return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}


def test_migration_adds_removed_at_columns_to_legacy_tables():
    engine = _legacy_engine()

    applied = ensure_removed_at_columns_on_engine(engine)

    assert applied is True
    with engine.connect() as conn:
        assert "removed_at" in _columns(conn, "films")
        assert "removed_at" in _columns(conn, "showings")


def test_migration_keeps_existing_rows():
    """Aggiungere la colonna non tocca le righe: lo storico resta consultabile."""
    engine = _legacy_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO films (id, title) VALUES (1, 'Film vecchio')")

    ensure_removed_at_columns_on_engine(engine)

    with engine.connect() as conn:
        row = conn.exec_driver_sql("SELECT id, title, removed_at FROM films").fetchone()
    assert row[0] == 1
    assert row[1] == "Film vecchio"
    assert row[2] is None  # riga viva: nessuna archiviazione d'iniziativa della migrazione


def test_migration_is_a_no_op_when_columns_already_exist():
    """Seconda esecuzione: nessuna modifica (può girare a ogni avvio del seed)."""
    engine = _legacy_engine()
    ensure_removed_at_columns_on_engine(engine)

    assert ensure_removed_at_columns_on_engine(engine) is False


def test_migration_skips_tables_that_do_not_exist_yet():
    """Tabella assente: la crea `create_all` con la colonna già dentro, qui non c'è nulla da fare."""
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as conn:
        assert ensure_removed_at_columns(conn) is False
