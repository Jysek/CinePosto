"""Re-export dei service per import piu' comodo dai router."""

from app.services import cinema_service, dataset_service, film_service

__all__ = ["cinema_service", "dataset_service", "film_service"]
