# Brief — `dataset_meta`: la freschezza viene dalla run, non dall'insert

**Obiettivo.** `GET /api/v1/dataset` deve dire *quando è girata la run che ha prodotto i dati nel DB*,
non *quando è stata inserita l'ultima riga*. Fonte unica: il `generated_at` di `showings.json`,
persistito dal seed in una tabella nuova `dataset_meta` (modello + repository + service, layering
`routers → services → repositories → models` rispettato).

## Fatti verificati (non ipotesi)

| Fatto | Prova |
|---|---|
| Lo scraper emette già `generated_at` in tutti i JSON | `scraper/scraper/models.py:174,212,233,243`; valore reale `2026-10-03T13:17:44.649380+02:00` |
| Oggi la fonte è `max(Showing.scraped_at)` = istante di insert | `backend/app/services/dataset_service.py:43` → `backend/app/repositories/showing_repo.py:123` |
| `showing_repo.upsert` non aggiorna `scraped_at` sulle righe esistenti | `backend/app/repositories/showing_repo.py` (upsert) |
| La tabella nuova non richiede migrazioni: `create_all` all'avvio la crea | `backend/app/main.py:27`; `backend/app/seed_from_json.py` `main()` |
| Le fixture dei test hanno già `generated_at` nei JSON | `backend/tests/test_seed_archive.py:50`, `test_seed_identity.py:53`, `test_cinema_maps_place_url.py:30` |
| Gate: Docker disponibile, `make lint` + `make test` (84 test backend) | `docker compose version` → v5.7.0 |
| L'app non cambia: il campo conserva nome e forma | `app/src/.../StaleDataBanner` legge `is_stale`/`latest_scraped_at` da `/dataset` |

## Decisioni chiuse (lock, approvate 2026-11-19)

**Q1 — Fonte della data: `generated_at` di `showings.json`.** L'endpoint misura la freschezza del
**palinsesto**; anagrafica e metadati (`cinemas.json`, `films.json`) non possono far sembrare fresco
un palinsesto vecchio.

**Q2 — `dataset_meta` vuota (DB seedato prima di questa modifica): fallback a
`max(Showing.scraped_at)`.** Un DB legacy continua a comportarsi come prima finché non rigira il seed,
invece di mostrare a tutti un banner falso. Fallback dichiarato nel docstring, in `api.md` e con un
warning nei log.

**Q3 — Nome del campo API invariato: `latest_scraped_at`.** Cambia solo la semantica; nessuna
modifica all'app, nessun nuovo campo.

**Q4 — `showings.json` senza `generated_at`: il seed fallisce, prima di qualsiasi scrittura.** Una run
che non sa dichiarare la propria età non è una run (stessa regola di `_parse_window`).

**Q5 — `GET /admin/dataset-info` allineato alla stessa fonte.** Due endpoint con lo stesso nome di
campo e due significati diversi si pagano al primo debug.

## Tappi ai buchi di queste scelte

| Buco | Tappo | Dove |
|---|---|---|
| Primo avvio: DB senza meta, si usa il ponte e la data può sbagliare di qualche ora | warning esplicito nei log a ogni uso del fallback + test dedicato + riga «dopo il deploy lancia il seed» in `api.md` e diario | `dataset_service.py`, `tests/test_routers.py`, docs |
| Scraper che smette di scrivere `generated_at`: con Q4 il seed notturno si ferma | validazione **prima** di ogni scrittura (errore pulito, zero righe toccate) + test «errore → zero scritture» + **test di contratto lato scraper** che i quattro JSON contengano `generated_at` con offset, così la regressione la ferma la CI dello scraper | `seed_from_json.py`, `tests/test_seed_dataset_meta.py`, `scraper/tests/test_models.py` |
| Fuso: `generated_at` è `+02:00`, SQLite non conserva il fuso | normalizzazione a UTC naive nel seed + test con fixture `+02:00` che verifica l'ora esatta | `seed_from_json.py`, test |
| Tabella che cresce a ogni seed: «quale riga è quella buona?» | riga unica `id=1` (upsert, non insert) + test che due seed lasciano una sola riga col valore più recente | `models/dataset_meta.py`, `dataset_meta_repo.py`, test |
| Seed morto a metà: data nuova che punta a dati non atterrati | scrittura della meta nella stessa transazione degli showings; rollback → resta la data dell'ultima run riuscita + test | `seed_from_json.py`, test |

## Criteri di successo

1. Dopo il seed, `dataset_meta` contiene **una** riga con il `generated_at` di `showings.json`
   normalizzato in UTC.
2. Run che non inserisce righe nuove → `is_stale: false` (test: righe con `scraped_at` di 10 giorni fa
   + `generated_at` di adesso).
3. Seed su JSON vecchi → `is_stale: true` anche se le righe sono appena state inserite (test:
   `generated_at` 48 h fa).
4. `dataset_meta` vuota → fallback a `max(scraped_at)` (test).
5. `showings.json` senza `generated_at` → `ValueError` esplicito, nessuna scrittura (test).
6. `make lint` e `make test` verdi; docs aggiornate; voce cancellata da `problemi-aperti.md`; riga di
   diario in coda a `stato-e-diario.md`.

## Esclusioni

- Nessuna modifica all'app, al nome del campo, alla soglia di 36 h, al comportamento di `is_stale`.
- Niente Alembic, niente modulo in `app/maintenance/`: la tabella è **nuova**, `create_all` basta.
- Nessuna riscrittura dei JSON dello scraper e nessuno scraping live.
- `app/overview.md` non si tocca: descrive già la semantica desiderata, che ora diventa vera.

Stile: full
