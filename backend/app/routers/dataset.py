"""Endpoint pubblico sullo stato del dataset (freschezza dei dati)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import DatasetInfo
from app.services import dataset_service

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.get("", response_model=DatasetInfo)
def dataset_info(db: Session = Depends(get_db)):
    """Riepilogo pubblico del dataset: conteggi e freschezza dei dati.

    Pubblico di proposito: l'app deve poter avvisare l'utente quando la
    programmazione non è aggiornata, e un token admin nel bundle JS non è un
    segreto. Nessun dato sensibile: solo conteggi e un timestamp.
    """
    return dataset_service.get_dataset_info(db)
