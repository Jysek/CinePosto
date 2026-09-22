# CinePosto — Stato attuale e diario

> Verificato su `0c56a7e` (`2026-09-21`).

**Come si usa questo file.** La sezione «Stato attuale» è una fotografia di oggi e si **riscrive**
quando cambia. La sezione «Diario» è **append-only**: si aggiunge in coda, non si riscrive mai il
passato e non si cancellano le righe precedenti.

## Stato attuale

**Cosa funziona end-to-end**: lo scraping delle sale coperte, il backend FastAPI e l'app Expo su
web, iOS e Android dalla stessa codebase. La CI testa backend, scraper e export web a ogni push.

| Area | Stato | Dove |
|---|---|---|
| Scraper | 8 connettori attivi | `scraper/copertura.md` |
| Backend | 11 endpoint REST, 31 test | `backend/api.md` |
| App | web + iOS + Android, dati dall'API | `app/overview.md` |
| Deploy | procedura pronta e verificata in locale, non ancora eseguita sulla VPS | `deploy.md` |

**In corso / prossimo passo**: estensione della copertura a tutte le sale dell'Umbria (8 connettori
su 30 sale note, 11 con sito noto e tecnica da analizzare — vedi `scraper/copertura.md`). Restano
aperti l'avviso "dati non aggiornati" nell'app e il primo deploy sulla VPS (`problemi-aperti.md`).

**Fuori scope per scelta**: account utente, acquisto biglietti in-app, notifiche push.

## Diario

Una riga per sessione, in coda. Formato: `- **<data>** — cosa è stato fatto, decisioni, note.`

- **2026-09-21** — creata la struttura di memoria della documentazione: questo diario, il registro
  `problemi-aperti.md`, l'indice `docs/index.md` rinnovato e l'intestazione di verifica su tutti i
  documenti vivi. Nessun cambiamento al codice.
- **2026-09-21** — bonifica dei documenti (Fase 3): allineati al codice il numero di sale (8), i test
  (141 scraper + 31 backend) e gli endpoint (11); corrette le famiglie di connettori in
  `panoramica.md` e `scraper/architecture.md`, le percentuali storiche in `api.md` e
  `scraper/architecture.md`, i comandi canonici in `AGENTS.md`; rimosso `integrazione-e-fix.md`
  (il contenuto vivo era già in `app/overview.md`; la pre-aggregazione del seed è ora in
  `schema-mapping.md` §3).
  Nessun cambiamento al codice. Restano da riscrivere `backend/architecture.md` e
  `schema-mapping.md` §7 (rinviati a una Fase 3-bis).
- **2026-09-21** — chiusi i residui della bonifica documentale (Fase 3-bis): riscritti gli endpoint
  reali e lo stato in `backend/architecture.md`, ripulite la checklist e l'esempio di
  `schema-mapping.md` (path `/film/42` e `showings` piatti, `language`/`screen` presenti nel JSON),
  ridotti a vetrina `backend/README.md` e `scraper/README.md`; corretti l'esempio JSON dell'API e il
  numero di test nel `Makefile`. Aperti in `problemi-aperti.md` il healthcheck a 3 fonti su 8 e il
  commento Alembic fuorviante nel lifespan.
  Nessun cambiamento al codice.
- **2026-09-22** — repository allineato e pubblicato: `origin/main` portato a `0e81e3c` (23 commit,
  cioè `b90e5c0` più la formattazione `ruff format` dei test dei connettori schema.org: la CI
  sarebbe altrimenti nata rossa sul job scraper). Controlli locali tutti verdi (31 test backend,
  141 scraper, coverage 75%, export web + `expo-doctor` 21/21, config di produzione valida). CI
  verde su entrambi i job:
  https://github.com/Jysek/CinePosto/actions/runs/35786979140. Il trunk di lavoro è `main`.