# Plan — `dataset_meta`: la freschezza viene dalla run di scraping

Contratto: [`plan-brief.md`](plan-brief.md) (obiettivo, fatti, decisioni chiuse Q1-Q5, tappi,
criteri di successo, esclusioni). Le decisioni sono approvate: 1A/2A e le tre minori.

## How to resume

- Stato: `grep '| Stato: TODO' docs/briefs/dataset-meta/plan.md` (col pipe: senza, il pattern pesca
  anche i criteri `done:`); si parte dal primo TODO la cui condizione è vera.
- Prima di leggere qualsiasi cosa: `git status --porcelain`. File modificati = lavoro in corso.
- Gate: `make lint` e `make test` (Docker, v5.7.0). Il Python locale non serve e non va usato.
- Trappole: (1) `max(Showing.scraped_at)` è **insert time**, non run time: è il difetto da chiudere,
  non la fonte; (2) SQLite restituisce datetime **naive UTC** — il fuso si normalizza nei confini
  (seed in ingresso, service in uscita), mai nel repository; (3) `dataset_meta` non vuole moduli in
  `app/maintenance/`: `Base.metadata.create_all` (`backend/app/main.py:27`) crea la tabella.
- Primo blocco: **0** (branch + commit del contratto). Nessun figlio parte prima.
- Figlio `failed` per timeout → `resume`, non rilancio; figlio `stopped` → si riparte dall'ultimo
  commit, mai da un albero mezzo modificato.

## Passi

- 0. Branch `feat/backend-dataset-meta` + commit di contratto, piano e riga in `docs/index.md` | files: `docs/briefs/dataset-meta/plan-brief.md`, `docs/briefs/dataset-meta/plan.md`, `docs/index.md` | done: `git log -1 --name-only` mostra i tre file, `git status --porcelain` vuoto | Stato: TODO
- 1. Modello `DatasetMeta` (riga singola `id=1`, `generated_at` DateTime NOT NULL naive-UTC, `seeded_at` server_default now) + export in `models/__init__` | files: `backend/app/models/dataset_meta.py`, `backend/app/models/__init__.py` | done: `docker compose run --rm backend python -c "from app.models import DatasetMeta; print(DatasetMeta.__tablename__)"` stampa `dataset_meta`; `make test` 84 verdi | Stato: TODO
- 2. Repository `dataset_meta_repo`: `upsert_generated_at(db, generated_at)` e `get_generated_at(db)`; export in `repositories/__init__` | files: `backend/app/repositories/dataset_meta_repo.py`, `backend/app/repositories/__init__.py` | done: import dal container stampa le due funzioni; `make lint` verde | Stato: TODO
- 3. Seed: `_parse_generated_at` (ISO con offset → UTC naive, `ValueError` se manca o è malformato) chiamato **prima** di qualsiasi scrittura, poi `dataset_meta_repo.upsert_generated_at` dentro la stessa transazione degli showings; test del seed | files: `backend/app/seed_from_json.py`, `backend/tests/test_seed_dataset_meta.py` | done: verdi i test su meta scritta in UTC (fixture `+02:00`), una sola riga dopo due seed, `ValueError` con zero scritture, rollback che conserva la data precedente | Stato: TODO
- 4. Service: legge `dataset_meta_repo.get_generated_at` e usa `showing_repo.latest_scraped_at` solo se la meta manca, con `logger.warning` esplicito; docstring del service e commenti dello schema riscritti (fonte = run) | files: `backend/app/services/dataset_service.py`, `backend/app/schemas/dataset.py` | done: `make test` verde; `grep -n "Limite noto" backend/app/services/dataset_service.py` non trova nulla | Stato: TODO
- 5. Test di contratto lato scraper: ogni output JSON contiene `generated_at` ISO con offset e si può parsare | files: `scraper/tests/test_models.py` | done: `make test-scraper` verde (185 + nuovo test) | Stato: TODO
- 6. Test dell'endpoint sulla nuova semantica + `admin/dataset-info` allineato alla stessa fonte | files: `backend/tests/test_routers.py`, `backend/app/routers/admin.py` | done: verdi i tre test — meta adesso con `scraped_at` di 10 giorni fa → non stale; meta 48 h fa con righe appena inserite → stale; meta assente → fallback con warning; `make test` verde | Stato: TODO
- 7. Docs lato dati: tabella `dataset_meta` e ordine del seed in `schema-mapping.md`; modello dati e sezione «Seed da JSON scraper» in `architecture.md` | files: `docs/backend/schema-mapping.md`, `docs/backend/architecture.md` | done: entrambi descrivono tabella, fonte `showings.json`, normalizzazione UTC, fallback; intestazione «Verificato su» aggiornata | Stato: TODO
- 8. Docs contratto API: §4.10 senza «limite noto», semantica di `latest_scraped_at` = istante della run, fallback, DB vuoto e «dopo il deploy lancia il seed» | files: `docs/backend/api.md` | done: `grep -n "Limite noto sulla fonte" docs/backend/api.md` vuoto; tabella campi ed esempi coerenti | Stato: TODO
- 9. Chiusura docs: voce cancellata da `problemi-aperti.md`, riga di sessione in coda a `stato-e-diario.md` | files: `docs/problemi-aperti.md`, `docs/stato-e-diario.md` | done: `grep -c "istante di insert" docs/problemi-aperti.md` = 0 e la voce non c'è più; ultima riga del diario è questa sessione con data e conteggi test reali | Stato: TODO
- 10. Gate, review a tre angoli, push | files: — | done: `make lint` + `make test` + `make test-scraper` verdi su albero pulito; review correttezza/sicurezza/coerenza-brief senza P0/P1 aperti; push del branch su `origin` | Stato: TODO

## Lanes

| Lane | Passi | File | Dipende da |
|---|---|---|---|
| A — base backend (padre) | 1, 2 | `backend/app/models/dataset_meta.py`, `backend/app/models/__init__.py`, `backend/app/repositories/dataset_meta_repo.py`, `backend/app/repositories/__init__.py` | passo 0 |
| B — scrittura backend (ondata 2, in parallelo) | 3 (W1), 4 (W2), 5 (W4) | `backend/app/seed_from_json.py` + `backend/tests/test_seed_dataset_meta.py`; `backend/app/services/dataset_service.py` + `backend/app/schemas/dataset.py`; `scraper/tests/test_models.py` | lane A committata |
| C — test endpoint + docs (ondata 3, in parallelo) | 6 (W3), 7 (D1), 8 (D2) | `backend/tests/test_routers.py` + `backend/app/routers/admin.py`; `docs/backend/schema-mapping.md` + `docs/backend/architecture.md`; `docs/backend/api.md` | lane B committata |
| D — chiusura (padre) | 9, 10 | `docs/problemi-aperti.md`, `docs/stato-e-diario.md` | lane C |

Shared, un solo padrone (il padre): `docs/briefs/**`, `docs/index.md`, `backend/app/models/__init__.py`,
`backend/app/repositories/__init__.py`, `docs/stato-e-diario.md`.
