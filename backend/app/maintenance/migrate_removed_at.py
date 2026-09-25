"""Migrazione minima: aggiunge la colonna `removed_at` a `films` e `showings`.

Perché esiste e non c'è Alembic: la regola di progetto dice che il DB è ricreabile
dal seed e quindi non servono migrazioni — ma qui il DB contiene **storico** che
l'utente vuole conservare («tra 2 anni lo stesso film torna al cinema e voglio
riusare/risalire ai dati vecchi»), quindi il DB non si ricrea da zero. Serve un
`ALTER TABLE` idempotente: aggiunge la colonna solo se manca, così può girare a
ogni avvio del seed senza effetti collaterali e senza perdere righe.

`removed_at` è la marca di **archiviazione** (soft delete): valorizzato = la riga
è fuori programmazione e non compare nelle query pubbliche; NULL = in programmazione.
Mai `DELETE`: i dati vecchi restano consultabili.

Uso:
- da solo:  `python -m app.maintenance.migrate_removed_at`
- dal seed: `ensure_removed_at_columns(db.connection())` (log quando applica davvero)
"""

from __future__ import annotations

import logging

from sqlalchemy.engine import Connection, Engine

logger = logging.getLogger(__name__)

# Tabelle che ricevono la colonna di archiviazione.
ARCHIVE_TABLES = ("films", "showings")


def ensure_removed_at_columns(conn: Connection) -> bool:
    """Aggiunge `removed_at` alle tabelle che non ce l'hanno. True se ha modificato qualcosa.

    Lavora su una connessione (non su un engine) per girare nello stesso
    contesto transazionale del chiamante: il seed la fa sua e la committa insieme
    ai dati, lo script standalone la apre e la chiude in `main()`.

    Se la tabella non esiste ancora la si salta: la crea `Base.metadata.create_all`
    con la colonna già dentro (il modello la dichiara), quindi non c'è nulla da
    migrare.
    """
    applied = False
    for table in ARCHIVE_TABLES:
        columns = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()}
        if not columns or "removed_at" in columns:
            continue
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN removed_at DATETIME")
        logger.info("Migrazione applicata: %s.removed_at aggiunta", table)
        applied = True
    return applied


def ensure_removed_at_columns_on_engine(engine: Engine) -> bool:
    """Versione standalone: apre e chiude la connessione da sola."""
    with engine.begin() as conn:
        return ensure_removed_at_columns(conn)


def main():
    """Uso standalone: python -m app.maintenance.migrate_removed_at"""
    from app.database import engine

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    applied = ensure_removed_at_columns_on_engine(engine)
    if applied:
        print("OK: migrazione applicata (colonne removed_at aggiunte)")
    else:
        print("OK: nessuna migrazione necessaria (le colonne removed_at esistono gia')")


if __name__ == "__main__":
    main()
