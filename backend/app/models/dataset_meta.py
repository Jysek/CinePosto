"""SQLAlchemy model: DatasetMeta (una riga: quando è girata la run importata)."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# La tabella descrive il dataset di oggi, non una storia di importazioni: una riga sola,
# con id fisso. La storia delle run sta nei JSON (`generated_at`) e nei log.
SINGLETON_ID = 1


class DatasetMeta(Base):
    """Metadati dell'ultima importazione: quando è girata la run che ha prodotto i dati.

    Prima di questa tabella la freschezza veniva da `max(Showing.scraped_at)`, cioè
    dall'istante in cui la riga più recente è stata **inserita**: una run che non
    inseriva righe nuove risultava vecchia, e un seed su JSON vecchi risultava fresco.
    `generated_at` è il `generated_at` di `showings.json` (l'istante dichiarato dalla
    run) normalizzato in UTC: SQLite non conserva il fuso, quindi dentro il DB si tiene
    un naive UTC e la conversione avviene al confine (seed in ingresso, service in uscita).
    """

    __tablename__ = "dataset_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Quando questa riga è stata scritta: serve a distinguere "run vecchia riletta dopo
    # giorni" da "seed appena eseguito", che `generated_at` da solo non racconta.
    seeded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
