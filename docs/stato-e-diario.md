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
- **2026-09-22** — chiuso il buco tra `make lint` e la CI: il target ora esegue anche
  `ruff format --check` (backend e scraper), cioè la stessa cosa del job Docker della CI; era la
  causa per cui il 22 settembre il lint locale risultava verde e la CI sarebbe nata rossa. Allineati
  `AGENTS.md` (§Definition of done) e `docs/development.md`, `development-windows.md`,
  `scraper/architecture.md`. Cancellato il branch locale residuo `chore/app-sdk-57` (già contenuto
  in `main`).
- **2026-09-23** — risolto il mojibake della console Windows (`make scrape` stampava
  `JSON aggiornati in scraper/output/ â€” ora: make seed`): i messaggi di `make` e degli script sono
  ora ASCII (era un problema di codifica console, non di battitura), con il nuovo target
  `make check-console` che impedisce regressioni e gira anche in CI; nota di troubleshooting in
  `development-windows.md` §9.
- **2026-09-23** — console dell'app pulita dai warning del nostro codice: il titolo dell'hero usa la
  shorthand `textShadow` al posto delle prop `textShadowColor/Offset/Radius` (deprecate in RN 0.86),
  lo splash usa `Platform.OS !== 'web'` per `useNativeDriver` (su web faceva ripiegare l'animazione
  sul thread JS con un warning) e la View di `FilmsTab` usa `style.pointerEvents` invece della prop
  deprecata. Verificato con Playwright sul dev server (i tre warning nostri non compaiono più) e a
  occhio su web: ombra e animazione invariate (screenshot prima/dopo identici, anche sull'export di
  produzione). Resta un warning equivalente dalla tab bar di React Navigation (voce in
  `problemi-aperti.md`); il messaggio su React DevTools è informativo e resta.
- **2026-09-23** — corretti i commenti che descrivevano codice inesistente: il docstring del
  `lifespan` non cita più Alembic (non configurato, e `create_all` non migra lo schema esistente) e
  dice il limite reale; sweep dei commenti "in prod / MVP / TODO" su backend e scraper con verdetti
  riportati in chat. Voce chiusa in `problemi-aperti.md`.
- **2026-09-23** — healthcheck esteso da 3 a 8 fonti: aggiunti i controlli per Zenith, Nuovo
  Cinema Castello, Concordia, Metropolis e la risoluzione del venue di The Space Terni; estratta
  `has_failures()` e creato `scraper/tests/test_healthcheck.py` (prima il file non aveva test, ed è
  la ragione per cui i 5 connettori nuovi non erano stati monitorati). Rimossa la voce da
  `problemi-aperti.md`. In più, a run reale erano emersi due falsi positivi (Concordia risponde
  in ~11s ma il check aveva timeout 10s; Castello con SSL transitorio): allineati timeout
  (`REQUEST_TIMEOUT`) e retry per errori di rete (`REQUEST_RETRY`/`RETRY_BACKOFF`, solo su
  eccezioni, mai su status HTTP) alle condizioni degli stessi connettori. Giro reale: 8/8 OK,
  exit 0.
