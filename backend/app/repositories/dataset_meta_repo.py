"""Repository della tabella `dataset_meta` (una riga: la run importata nel DB).

Nessuna trasformazione di fuso qui: il repository legge e scrive quello che riceve.
La normalizzazione a UTC sta nel seed (ingresso) e nel service (uscita).
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset_meta import SINGLETON_ID, DatasetMeta


def _now_utc_naive() -> datetime:
    """Orologio del seed: naive UTC, la convenzione del resto del DB."""
    return datetime.now(UTC).replace(tzinfo=None)


def upsert_generated_at(db: Session, generated_at: datetime) -> DatasetMeta:
    """Scrive (o aggiorna) la riga unica con l'istante della run importata.

    Una riga per costruzione: aggregare per insert produrrebbe una storia di importazioni
    e un errore di lettura dovrebbe scegliere "la riga giusta" fra tante. L'upsert è
    idempotente, quindi l'idempotenza del seed resta vera anche per la freschezza.

    `seeded_at` si valorizza a ogni scrittura, non solo all'insert: `server_default`
    scatta solo sulla prima riga, e dal secondo seed in poi il campo indicherebbe la
    data del primo seed — proprio la diagnosi che serve a capire se il timer e' vivo.
    """
    now_utc = _now_utc_naive()
    row = db.get(DatasetMeta, SINGLETON_ID)
    if row is None:
        row = DatasetMeta(id=SINGLETON_ID, generated_at=generated_at, seeded_at=now_utc)
        db.add(row)
    else:
        row.generated_at = generated_at
        row.seeded_at = now_utc
    db.flush()
    return row


def get_generated_at(db: Session) -> datetime | None:
    """Istante della run importata, `None` se il seed non ha mai scritto la tabella.

    `None` è uno stato legittimo (DB seedato prima di questa tabella): il service decide
    come degradare. Il valore è naive UTC, come il resto del DB.
    """
    return db.scalar(select(DatasetMeta.generated_at).where(DatasetMeta.id == SINGLETON_ID))
