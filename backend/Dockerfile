# Backend CinePosto — FastAPI + SQLAlchemy + SQLite
#
# Python 3.12 non è una preferenza ma un vincolo: pydantic-core 2.27 usa PyO3 0.22,
# che non compila su 3.13+/3.14 (vedi backend/requirements.txt).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Solo le dipendenze in questo layer: resta in cache finché requirements.txt non cambia.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Utente non privilegiato: lo usa la produzione (compose.prod.yaml).
# In sviluppo si resta root, perché i bind mount di Windows non gestiscono la ownership.
# /data è la directory del DB SQLite: l'ownership viene ereditata dal volume alla creazione.
RUN useradd --create-home --uid 1000 app && mkdir -p /data && chown app:app /data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
