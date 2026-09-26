# CinePosto — Stato attuale e diario

> Verificato su `056f04f` (`2026-09-26`).

**Come si usa questo file.** La sezione «Stato attuale» è una fotografia di oggi e si **riscrive**
quando cambia. La sezione «Diario» è **append-only**: si aggiunge in coda, non si riscrive mai il
passato e non si cancellano le righe precedenti.

## Stato attuale

**Cosa funziona end-to-end**: lo scraping delle sale coperte, il backend FastAPI e l'app Expo su
web, iOS e Android dalla stessa codebase. La CI testa backend, scraper e export web a ogni push.

| Area | Stato | Dove |
|---|---|---|
| Scraper | 8 connettori attivi | `scraper/copertura.md` |
| Backend | 11 endpoint REST, 70 test | `backend/api.md` |
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
- **2026-09-24** — ricontrollo del contenuto dei documenti vivi (16 file dichiaravano
  `Verificato su 0c56a7e` senza essere stati riletti): corretti i path inesistenti in
  `backend/api.md` (`app/api/client.js` → `app/src/api/api.js`, `app/api/schemas.js` inesistente)
  e l'esempio di PostModernissimo in `api.md`/`schema-mapping.md` (indirizzo e coordinate non
  allineati a `config.py`); allineati anche la tabella "Quando caricare cosa" e i default CORS di
  `api.md`, la tabella del client e i loghi in `app/overview.md`, i nomi delle fixture nel README
  dei connettori, i percorsi del deploy in `scraper/architecture.md`. Numeri aggiornati a 149 test
  scraper e 180 totali (panoramica, development-windows, README, AGENTS.md). Eseguito davvero
  `make prod-test` (Caddy + TLS self-signed, 8443 OK); emerso che `make prod-down` fallisce senza
  le variabili d'ambiente: nuova voce in `problemi-aperti.md` (proposto fix nel Makefile, non
  toccato in questa fase). Intestazioni aggiornate ai commit di correzione; per
  `development-windows.md` §5 e per le schede connettori resta dichiarata esplicitamente la parte
  non rieseguita (markup dei siti non ri-verificato, nessuno scraping live).
- **2026-09-24** — fix di `make prod-down` (proposto e approvato nella sessione del ricontrollo):
  `compose.prod.yaml` pretende `ADMIN_TOKEN`/`CORS_ORIGINS` con `:?` gia' all'interpretazione del
  file, quindi anche un `down` falliva; estratte le variabili fittizie in `PROD_DUMMY_ENV` e
  usate in `prod-test` e `prod-down` (stessi valori di prima per `prod-test`). Verificato:
  `make prod-test` → 8443 OK, `make prod-down` → exit 0. Voce cancellata da
  `problemi-aperti.md`; nota obsoleta rimossa da `deploy.md`.
- **2026-09-23** — fusi i doppioni di film già nel DB: la chiave naturale del backend ora unisce
  `&`/`e` e adotta l'anno nullo, e un nuovo script di manutenzione
  (`python -m app.maintenance.dedup_films`, dry-run di default) ricalcola le chiavi e fonde i gruppi
  certi (nel DB: le due righe di `AMORI & INCANTESIMI 2` / `Amori e incantesimi 2` → una sola, con
  gli orari della run più recente 16:00: 4 showings ri-assegnati, 4 scartati, 1 riga rimossa) con
  report di ciò che scarta e dei candidati da approvare a mano con `--merge`. Verificato su API
  (`/film/oggi` e `/film/search` → una voce sola) e home dell'app (una scheda). Restano aperti i
  duplicati da varianti di titolo fra fonti diverse (coppie 29/68 `CARS` e 42/53 `Talking Tom
  Heroes`) e i residui delle run passate.
- **2026-09-23** — lo scraper non pubblica più due volte lo stesso film: nuova fusione per
  `wikidata_id` **dopo** l'arricchimento (prima non era possibile: la dedup girava prima di
  Wikidata e due varianti arricchite avrebbero violato `UNIQUE(wikidata_id)` facendo fallire il
  seed), più una tabella di alias curata (`scraper/scraper/title_aliases.py`, prima voce: le due
  forme del titolo di *Cars* fra The Space/UCI e Metropolis); il titolo del master è scelto in
  modo deterministico (preferisce la forma non urlata). Corretto anche `normalize_title`: non
  taglia più le cifre finali e `fuzzy_match` non fonde un sequel numerato col primo film (effetto
  sui JSON di oggi: 1 film cambia `id`, `Amori e incantesimi` → `Amori e incantesimi 2`, più i suoi
  4 `film_id` in `showings.json` e la voce di stato di `movies.json`: 3 file, 7 righe). Fusa la
  coppia CARS nel DB con `dedup_films --merge 29:68 --apply` (2 showings ri-assegnati, `year=2006`
  adottato, 1 riga rimossa): `GET /api/v1/film/oggi` → 23 film con una sola scheda CARS. Test 149 →
  162. Nuove voci in `problemi-aperti.md`: sequel con numeri romani (ancora fondono) e arricchimento
  Wikidata che non aggancia i titoli urlati (radice degli alias). I JSON restano quelli del
  2026-09-20: la run di rigenerazione va fatta solo su autorizzazione esplicita.
- **2026-09-25** — rigenerati i JSON con la run di scraping autorizzata del 25/09 (40 film, 449
  showings, 0 errori di scraping, `validate_output.py` senza errori critici) e committati come
  fixture. Dalla run e dai controlli sull'app sono emersi 6 difetti/richieste, pianificati come
  `fase-15`…`fase-20` in `pianificazione/`: (1) Cars compare in 3 schede, (2) coppie doppie anche per
  Heart of the Beast/Oceania/Ultimo/The Invite per i residui del DB (82 film nel DB contro 40 nei
  JSON), (3) "Leggi di più/Mostra meno" inutile nella trama, (4) il popup della mappa non apre Google
  Maps, (5) al posto delle coordinate serve la place URL del cinema su Maps, (6) 4 descrizioni tronche
  a 103 caratteri (Naza, Una storia, Ritorno a Buenos Aires, I figli della scimmia — tutte da
  PostModernissimo). Decisioni prese: i residui del DB si **archiviano** con `removed_at`, mai si
  cancellano; al posto della sola tabella alias serve un match più robusto; le 8 place URL si
  raccolgono a mano (review dell'utente). Nota: `fase-12` è superata dalla `fase-16`.
- **2026-09-25** — fase-15: una sola scheda per *Cars*. Il giudizio «sono lo stesso film?» è unico,
  `match_cross_source` (`title_aliases.py`), con tre prove in **OR** — alias curato, `fuzzy_match`
  sulle forme grezze, `fuzzy_match` sulle forme canoniche — e non più in sequenza: prima l'alias
  sostituiva il titolo prima del confronto e spegneva il contenimento fra «Cars - Motori Ruggenti»
  e «CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO», così la riedizione del 20° anniversario restava
  in più schede. `_deduplicate_films` raggruppa inoltre per chiusura transitiva (se A~B e B~C, anche
  A e C sono lo stesso film): senza questa il numero di schede dipendeva dall'ordine dei connettori,
  perché la forma breve e «Cars – 20esimo anniversario» non si somigliano — è la forma lunga a fare
  da ponte. Nessuna voce nuova nell'alias (la terza forma la unisce il contenimento). I JSON non
  sono stati rigenerati (run live solo su richiesta): l'effetto si vedrà alla prossima run
  autorizzata; i residui del DB restano di competenza `fase-16`. I sequel con numeri romani
  («Rocky II») fondono ancora: test `xfail` che rimanda alla voce di `problemi-aperti.md`, non
  risolti qui. Test scraper 162 → 173 casi (168 funzioni).
- **2026-09-25** — CI riparata: `expo-doctor` falliva per il drift upstream del patch di `expo`
  (lockfile 57.0.24 contro `~57.0.25` richiesto dal SDK) e il job App era rosso su qualsiasi push,
  senza legame con le modifiche in corso. Aggiornato solo `package-lock.json` (`npm update expo`,
  spec `^57` invariato): `expo-doctor` 21/21 ed export web verdi. Commit `chore(app)` separato
  dalla fase-15, perché le dipendenze non si mescolano a una feature.
- **2026-09-25** — fase-16: i residui del DB si **archiviano**, mai si cancellano. Colonne
  `removed_at` su `films`/`showings`, arrivate con una migrazione `ALTER TABLE` **idempotente**
  (`app/maintenance/migrate_removed_at.py`): niente Alembic perché il DB contiene storico e non si
  ricrea dal seed. Dopo l'upsert il seed **riconcilia**: le righe non più nei JSON dell'ultima
  importazione si archiviano (film: assenza della chiave naturale `(title_normalized, year)`;
  showings: solo dentro la finestra `date_from`/`date_to` e per i cinema di `cinemas.json`), quelle
  che ricompaiono si riattivano. Guardia anti-fonte-rotta per cinema (`seed_archive_min_ratio` =
  0.5): sotto soglia l'archiviazione si salta e finisce in `skipped_cinemas`. Tutte le letture
  pubbliche filtrano `removed_at IS NULL` — compresi gli showings dei film archiviati — e `removed_at`
  non è esposto dall'API. Report `archived_*`/`reactivated_*`/`skipped_cinemas` nel return del seed
  e in `make seed`. Prima run sul DB di sviluppo: **42 film archiviati, 59 showings archiviati,
  0 riattivati, nessun cinema saltato**; seconda run: tutto a 0 (idempotente). Dall'API sono sparite
  le coppie doppie della tabella di fase-16 (Talking Tom comprese); restano le due «Cars» che
  vivono **nei JSON** (fase-15: la fusione si vedrà alla prossima run autorizzata). Test backend
  48 → 60 (archiviazione, guardia, idempotenza, filtri pubblici, migrazione).
- **2026-09-25** — registrato il rischio di duplicazione/crash del seed per `wikidata_id`, emerso
  chiudendo la fase-16: `upsert_from_scraper` risolve l'identità solo per chiave naturale
  (`film_repo.py:101`), quindi un film tornato con un titolo nuovo ma lo stesso `wikidata_id` di
  una riga già nel DB (anche archiviata) fa esplodere `make seed` con `IntegrityError: UNIQUE
  constraint failed: films.wikidata_id`; stesso esito se il `wikidata_id` arriva in update su una
  riga che non lo possiede (aggiornare la chiave di una riga trovata per wikidata aprirebbe invece
  la porta ai doppioni: scenario N/N+1/N+2 di Cars). Riprodotto in-memory, nessun dato reale toccato
  (0 conflitti sui dati del 25/09). Nessun codice cambiato in questa sessione: scritta
  `pianificazione/fase-21` — guardia di identità a due segnali (chiave naturale, poi `wikidata_id`),
  riuso della riga trovata per wikidata **senza cambiarle la chiave**, mai INSERT in conflitto
  (il conflitto si segnala, non si risolve da soli), invariante di fine seed con `identity_conflicts`
  e `duplicate_titles` nel report, già nel formato `dedup_films --merge A:B`. Voce con la prova in
  `problemi-aperti.md`.
- **2026-09-25** — **fase-21 eseguita**: guardia di identità del seed, un film = una riga.
  `upsert_from_scraper` risolve l'identità con due segnali (chiave naturale, poi `wikidata_id`): il
  film tornato con un titolo nuovo **riusa** la sua riga (mai INSERT, mai cambio di chiave né di
  titolo — la stabilità della chiave è la difesa contro i doppioni), il conflitto fra i due segnali
  non scrive `wikidata_id` da nessuna parte e si segnala. Report del seed con `identity_conflicts` e
  `duplicate_titles` nel formato `dedup_films --merge A:B` + invariante certificata a fine seed
  (0 coppie con lo stesso `wikidata_id`). Prima run sul DB reale: **0 conflitti, 0 coppie con anno
  NULL**, contatori di archiviazione a 0 (nessun dato toccato). Casi A/B/C riprodotti nei test:
  test backend 60 → 68. Voce del rischio `wikidata_id` cancellata da `problemi-aperti.md`.
- **2026-09-26** — **fase-20 eseguita**: le descrizioni tronche del PostModernissimo arrivano
  intere. Il campo `content` del payload RSC non era mai estratto (`_parse_rsc_payload` leggeva
  solo `details`/`shows`), quindi scattava sempre la meta description del CMS, tagliata a ~100
  caratteri a metà parola; ora `_extract_content` legge la sinossi intera dal payload e
  `fetch_film_detail` cerca **prima il paragrafo e poi la meta** (dal più completo al più debole).
  Aggiunta la regola di **non-degrado** (`pick_fuller_description`) nel delta e nella fusione
  cross-fonte, e `_pick_fuller_synopsis` nell'`upsert_from_scraper` del backend: una sinossi
  intera non si sovrascrive con una tronca. Un dettaglio che fallisce ora finisce in
  `ScrapeResult.errors` (fase `detail`) senza rompere la run. Nessuna run live e nessuna fetch
  diagnostica in questa sessione: i test usano fixture RSC/HTML registrate. Test scraper
  173 → 181 (180 pass + 1 xfail), backend 68 → 70. Guarigione dei dati: nei JSON ci sono **7**
  descrizioni da 103 caratteri (il caso citato era `Naza`; il dataset nel frattempo è cresciuto),
  il DB si sistema alla prossima run autorizzata + `make seed`. Restano **10 film senza
  descrizione** (`MATRIX 4K`, `Maigret, l'amore e la morte`, `Dov'è la Fiesta?`,
  `A Fox Under a Pink Moon`, `PerSo Short Award`, `Como tú me ves`, `Un solco nella terra`,
  `Indietro così!`, `Torneranno i lupi`, `Una cosa vicina`): problema diverso, annotato per una
  fase futura. Scheda nuova: `docs/scraper/connettori/postmodernissimo.md`.
