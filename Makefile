# CinePosto — comandi di sviluppo.
#
# Il Makefile è una scorciatoia, non un requisito: ogni target riporta il comando
# `docker compose` equivalente, così il progetto resta usabile anche senza `make`.
#
# Prima di tutto serve Docker Desktop avviato (su Windows: apri Docker Desktop e aspetta
# che l'icona smetta di girare).

COMPOSE      := docker compose
COMPOSE_PROD := docker compose -f compose.yaml -f compose.prod.yaml
BACKEND      := $(COMPOSE) run --rm backend
SCRAPER      := $(COMPOSE) run --rm scraper
API          := http://localhost:8000

# compose.prod.yaml pretende ADMIN_TOKEN e CORS_ORIGINS con `:?`, e il controllo scatta
# gia' quando Docker Compose interpreta il file: senza queste variabili non funziona
# nemmeno un `down`. I valori qui sotto servono solo a soddisfare l'interpolazione
# (in produzione i veri segreti arrivano da .env.prod, vedi prod-up).
PROD_DUMMY_ENV := DOMAIN=localhost ADMIN_TOKEN=test-locale CORS_ORIGINS='["https://localhost:8443"]'

# ── Shell delle ricette ───────────────────────────────────────────────────────
# Su Windows `bash` preso dal PATH può risolversi in quello di WSL, la cui distro
# di default (`docker-desktop`) non ha /bin/bash: da PowerShell `make dev` falliva
# con "execvpe(/bin/bash) failed". Usiamo il bash di Git per TUTTE le ricette, così
# `make` funziona identico da PowerShell, Git Bash e cmd. Il percorso 8.3
# (PROGRA~1) evita gli spazi, che `make` non sa gestire in SHELL.
ifeq ($(OS),Windows_NT)
  BASH := C:/PROGRA~1/Git/bin/bash.exe
  ifeq ($(wildcard $(BASH)),)
    BASH := bash
  endif
  SHELL := $(BASH)
else
  BASH := bash
endif

.DEFAULT_GOAL := help
.PHONY: help dev check-app-web check-console up down restart logs ps build shell test test-scraper lint seed scrape health prod-test prod-up prod-scrape prod-seed prod-down clean

help: ## Mostra questo aiuto
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

dev: ## AVVIA TUTTO: Docker (se spento), backend e app per browser e telefono
	@"$(BASH)" scripts/dev.sh

check-app-web: ## Verifica l'export web: build + server statico su :3000 (richiede: make up && make seed)
	@"$(BASH)" scripts/check-app-web.sh

up: ## Avvia il backend in background  ->  docker compose up -d --build backend
	$(COMPOSE) up -d --build backend
	@echo "Backend su $(API) - Swagger: $(API)/docs"

down: ## Ferma lo stack  ->  docker compose down
	$(COMPOSE) down

restart: ## Riavvia il backend  ->  docker compose restart backend
	$(COMPOSE) restart backend

logs: ## Segue i log del backend  ->  docker compose logs -f backend
	$(COMPOSE) logs -f backend

ps: ## Stato dei container  ->  docker compose ps
	$(COMPOSE) ps

build: ## Ricostruisce le immagini  ->  docker compose build
	$(COMPOSE) build

shell: ## Shell nel container backend  ->  docker compose run --rm backend bash
	$(BACKEND) bash

test: ## Test del backend (60)  ->  docker compose run --rm backend python -m pytest tests/ -q
	$(BACKEND) python -m pytest tests/ -q

test-scraper: ## Test dello scraper  ->  docker compose run --rm scraper python -m pytest tests/ -q
	$(SCRAPER) python -m pytest tests/ -q

lint: ## Ruff (check + format) su backend e scraper
	$(COMPOSE) run --rm backend python -m ruff check app/ tests/
	$(COMPOSE) run --rm backend python -m ruff format --check app/ tests/
	$(SCRAPER) python -m ruff check scraper/ tests/
	$(SCRAPER) python -m ruff format --check scraper/ tests/

seed: ## Popola il DB dai JSON committati  ->  docker compose run --rm backend python -m app.seed_from_json
	$(BACKEND) python -m app.seed_from_json

scrape: ## Scraping LIVE di tutti i cinema (etichetta: pochi giri al giorno)
	$(SCRAPER) python -m scraper.main --once
	@echo "JSON aggiornati in scraper/output/ - ora: make seed"

health: ## Verifica che il backend risponda
	@curl -s -o /dev/null -w "GET /health -> HTTP %{http_code}\n" $(API)/health

prod-test: ## Prova la configurazione di produzione in locale (Caddy + TLS self-signed su 8443)
	$(PROD_DUMMY_ENV) TLS_DIRECTIVE="tls internal" HTTP_PORT=8080 HTTPS_PORT=8443 \
	$(COMPOSE_PROD) up -d --build
	@echo "Attendi qualche secondo, poi: curl -k https://localhost:8443/health"
	@echo "Per fermarla: make prod-down"

prod-up: ## Avvia in produzione (legge .env.prod: ADMIN_TOKEN, CORS_ORIGINS, DOMAIN)
	$(COMPOSE_PROD) --env-file .env.prod up -d --build

prod-scrape: ## Primo scrape reale in produzione  ->  crea i JSON in ./data/output
	$(COMPOSE_PROD) --env-file .env.prod run --rm scraper

prod-seed: ## Popola il DB di produzione dai JSON in ./data/output
	$(COMPOSE_PROD) --env-file .env.prod run --rm backend python -m app.seed_from_json

prod-down: ## Ferma la produzione
	$(PROD_DUMMY_ENV) $(COMPOSE_PROD) down

clean: ## Ferma tutto e cancella DB locale e volumi  ->  docker compose down -v
	$(COMPOSE) down -v --remove-orphans
	@rm -f backend/data/cineposto.db && echo "DB locale rimosso"

# Controllo di regressione: i messaggi che finiscono a schermo devono restare ASCII.
# La console di Windows usa CP850, non decodifica l'UTF-8 e trasforma l'em dash in "â€”".
# La regola vale per le righe non-commento (i commenti restano UTF-8: li legge un editor).
check-console: ## Verifica che i messaggi di console siano ASCII (niente mojibake su Windows)
	@fail=0; \
	for f in Makefile dev.cmd scripts/*.sh; do \
	  out=$$(grep -vnE '^[[:space:]]*(#|REM)' "$$f" | grep -P '[\x80-\xFF]'); \
	  if [ -n "$$out" ]; then \
	    echo "ERRORE: caratteri non ASCII in $$f (righe non-commento):"; \
	    echo "$$out"; \
	    fail=1; \
	  fi; \
	done; \
	[ "$$fail" -eq 0 ] || { echo "I messaggi di console devono essere ASCII: la console di Windows (CP850) non legge UTF-8."; exit 1; }; \
	echo "Messaggi di console ASCII: OK"
