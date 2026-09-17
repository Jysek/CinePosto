# Scraper CinePosto — pipeline Python che produce i JSON di programmazione.
#
# Niente Chromium in questa immagine: `cloakbrowser` è usato solo come fallback (The Space)
# e porterebbe ~1,5 GB. Senza i binari il fallback fallisce in modo pulito: l'errore finisce
# in ScrapeResult.errors e gli altri cinema vengono comunque raspati.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Installazione editable (codice in /app, non in site-packages): in sviluppo /app è
# bind-montato, quindi le modifiche al codice sono attive senza ricostruire l'immagine.
COPY pyproject.toml ./
COPY scraper ./scraper
ARG INSTALL_EXTRAS="[dev]"
RUN pip install -e ".${INSTALL_EXTRAS}"

# Il resto del progetto serve a test e diagnostica, non all'installazione.
COPY tests ./tests
COPY healthcheck.py report.py validate_output.py ./

ENV SCRAPER_TZ=Europe/Rome

CMD ["python", "-m", "scraper.main", "--once"]
