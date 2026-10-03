"""Pydantic schemas Dataset — DTO API response per lo stato del dataset."""

from pydantic import BaseModel


class DatasetInfo(BaseModel):
    """Riepilogo pubblico del dataset: conteggi e freschezza dei dati.

    Pubblico di proposito: l'app deve poter avvisare l'utente quando la
    programmazione non è aggiornata. Nessun dato sensibile: conteggi e un
    timestamp.
    """

    # Istante della run di scraping che ha prodotto i dati oggi nel DB
    # (ISO con offset UTC). `null` se non c'è nessun dato. Vedi il docstring di
    # dataset_service.get_dataset_info per il limite sulla fonte attuale.
    latest_scraped_at: str | None
    # Ore trascorse da latest_scraped_at. `null` se non c'è nessun dato.
    age_hours: float | None
    # Vero se non c'è nessun dato oppure i dati superano la soglia di freschezza.
    # La regola di dominio è calcolata dal backend: il client la mostra e basta.
    is_stale: bool
    # Soglia applicata, esplicita: il client non deve indovinarla.
    stale_after_hours: int
    showings: int
    cinemas: int
