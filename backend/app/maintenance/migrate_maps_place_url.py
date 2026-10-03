"""Migrazione minima: aggiunge la colonna `maps_place_url` a `cinemas`.

Stessa ragione di `migrate_removed_at.py` e stessa forma: il DB conserva dati che
non si ricreano dal seed (qui: le righe `cinemas` e le loro relazioni), quindi
niente Alembic — un `ALTER TABLE` idempotente che può girare a ogni avvio del
seed senza effetti collaterali. `maps_place_url` nullable: un cinema senza la
place URL di Google Maps non è un errore, l'app usa il fallback a coordinate.

Uso:
- da solo:  `python -m app.maintenance.migrate_maps_place_url`
- dal seed: `ensure_maps_place_url_column(db.connection())`
"""

from __future__ import annotations

import logging

from sqlalchemy.engine import Connection, Engine

logger = logging.getLogger(__name__)


def ensure_maps_place_url_column(conn: Connection) -> bool:
    """Aggiunge `cinemas.maps_place_url` se manca. True se ha modificato qualcosa.

    Se la tabella non esiste ancora la si salta: la crea `Base.metadata.create_all`
    con la colonna già dentro (il modello la dichiara), quindi non c'è nulla da
    migrare.
    """
    columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(cinemas)").fetchall()}
    if not columns or "maps_place_url" in columns:
        return False
    conn.exec_driver_sql("ALTER TABLE cinemas ADD COLUMN maps_place_url VARCHAR")
    logger.info("Migrazione applicata: cinemas.maps_place_url aggiunta")
    return True


def ensure_maps_place_url_column_on_engine(engine: Engine) -> bool:
    """Versione standalone: apre e chiude la connessione da sola."""
    with engine.begin() as conn:
        return ensure_maps_place_url_column(conn)


def main():
    """Uso standalone: python -m app.maintenance.migrate_maps_place_url"""
    from app.database import engine

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    applied = ensure_maps_place_url_column_on_engine(engine)
    if applied:
        print("OK: migrazione applicata (colonna cinemas.maps_place_url aggiunta)")
    else:
        print("OK: nessuna migrazione necessaria (la colonna maps_place_url esiste gia')")
