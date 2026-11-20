"""Pydantic schemas Dataset — DTO API response per lo stato del dataset."""

from pydantic import BaseModel


class DatasetInfo(BaseModel):
    """Riepilogo pubblico del dataset: conteggi e freschezza dei dati.

    Pubblico di proposito: l'app deve poter avvisare l'utente quando la
    programmazione non è aggiornata. Nessun dato sensibile: conteggi e un
    timestamp.
    """

    # Istante della run di scraping che ha prodotto i dati oggi nel DB: il
    # `generated_at` di showings.json, scritto dal seed in `dataset_meta`
    # (ISO con offset UTC). `null` se non c'è nessun dato. Il nome del campo resta
    # `latest_scraped_at` per non rompere il client, ma la semantica è la run e non
    # l'insert: il fallback su max(Showing.scraped_at) è in
    # dataset_service.get_dataset_info.
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
