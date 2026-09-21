# CinePosto — Backend (FastAPI)

API REST che serve le programmazioni raccolte dallo scraper, leggendo un DB SQLite
popolato dai JSON in `scraper/output/`. Componente del monorepo CinePosto.

- **Contratto API** (endpoint, tipi, esempi fetch): [`docs/backend/api.md`](../docs/backend/api.md)
- **Architettura e modello dati**: [`docs/backend/architecture.md`](../docs/backend/architecture.md)
- **Mapping JSON scraper → DB**: [`docs/backend/schema-mapping.md`](../docs/backend/schema-mapping.md)
- **Storia, decisioni e problemi aperti**: [`docs/stato-e-diario.md`](../docs/stato-e-diario.md)

Swagger UI all'avvio: `http://localhost:8000/docs`.

## Comandi

```bash
make up       # avvia backend + DB (Docker)
make seed     # popola il DB dai JSON committati
make test     # 31 test (pytest)
make lint     # ruff
```

Senza Docker, dal progetto (Python 3.12): `python -m app.seed_from_json` per il seed,
`uvicorn app.main:app --reload --port 8000` per l'avvio. Dettagli in
[`docs/development.md`](../docs/development.md).

## Struttura

```
routers/       PRESENTATION: HTTP + validazione Pydantic
services/      BUSINESS: orchestrazione e regole di dominio
repositories/  DATA ACCESS: query SQLAlchemy
models/        DOMAIN: entità SQLAlchemy (SQLite)
schemas/       DTO Pydantic (input/output API, distinti dai modelli ORM)
```

Layering stretto: ogni layer chiama solo quello immediatamente sotto (regola di `AGENTS.md`).
I dati dei cinema arrivano dallo scraper: il backend non fa re-scraping.

## Test

`make test` → **31 test**: `test_config` 5, `test_repositories` 14, `test_routers` 12.
Girano su SQLite in-memory con `dependency_overrides` di `get_db`.
