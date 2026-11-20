"""Repository della tabella `dataset_meta` (una riga: la run importata nel DB).

Nessuna trasformazione di fuso qui: il repository legge e scrive quello che riceve.
La normalizzazione a UTC sta nel seed (ingresso) e nel service (uscita).
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dataset_meta import SINGLETON_ID, DatasetMeta


def upsert_generated_at(db: Session, generated_at: datetime) -> DatasetMeta:
    """Scrive (o aggiorna) la riga unica con l'istante della run importata.

    Una riga per costruzione: aggregare per insert produrrebbe una storia di importazioni
    e un errore di lettura dovrebbe scegliere "la riga giusta" fra tante. L'upsert è
    idempotente, quindi l'idempotenza del seed resta vera anche per la freschezza.
    """
    row = db.get(DatasetMeta, SINGLETON_ID)
    if row is None:
        row = DatasetMeta(id=SINGLETON_ID, generated_at=generated_at)
        db.add(row)
    else:
        row.generated_at = generated_at
    db.flush()
    return row


def get_generated_at(db: Session) -> datetime | None:
    """Istante della run importata, `None` se il seed non ha mai scritto la tabella.

    `None` è uno stato legittimo (DB seedato prima di questa tabella): il service decide
    come degradare. Il valore è naive UTC, come il resto del DB.
    """
    return db.scalar(select(DatasetMeta.generated_at).where(DatasetMeta.id == SINGLETON_ID))
