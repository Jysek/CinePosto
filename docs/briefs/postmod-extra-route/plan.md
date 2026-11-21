# PostModernissimo — la route `/extra/` non esiste più

`Stile: full` · Classe `M` · 2026-11-20 · branch `main`

## How to resume

1. `git status --porcelain` prima di tutto: i quattro JSON in `scraper/output/` sono sporchi della
   run di prova del 2026-11-20 e vanno committati solo al passo 3, riparati.
2. Leggi questo file, poi `grep '| Stato: TODO' docs/briefs/postmod-extra-route/plan.md` e parti dal
   primo TODO la cui condizione è vera.
3. Gate: `make lint` e `make test-scraper` (Docker). Fallback senza Docker:
   `python3 -m ruff check scraper/ tests/` + `format --check`, `python3 -m pytest tests/ -q` da `scraper/`.
4. Nessuno scraping live: la run è già stata fatta il 2026-11-20 e i JSON sono in `scraper/output/`.
   I fatti sul sito (404 su `/extra/`, 200 su `/films/`) sono nella chat del 2026-11-20 e in
   `scraper/output/errors.json`.
5. Un passo `DONE` è verificato quando il suo `done:` è vero su quell'albero, non "a occhio".

## Brief

**Obiettivo**. Le proiezioni che il sito espone solo sotto la vecchia route `/extra/` devono uscire
con un link che funziona (la pagina `/films/<slug>` del film indicato) e senza le due richieste
finite a 404 a ogni run. Gli orari restano: sono veri e altrimenti persi.

**Vincoli**.
- Il connettore continua a non sollevare per errori di rete/parsing: gli errori si raccolgono in
  `ScrapeResult.errors`, ma dopo il fix una route morta non deve generare una richiesta.
- I record sotto `/eventi/` restano scartati: sono eventi, non film (comportamento attuale).
- Nessuno scraping live in questa sessione.
- Un solo file di codice e un solo file di test: nessun refactor diffuso.

**Decisioni chiuse** (domanda -> risposta, round 1 del 2026-11-20).

1. Quale link mostra l'app su quelle proiezioni -> **la pagina `/films/<slug>`** indicata dal vecchio
   indirizzo. Conseguenza: il link porta al film, non alla rassegna.
2. "Prince of Broadway" il 23/11 21:30 e il 24/11 21:00 -> **una sola scheda con due date**.
   Conseguenza: le proiezioni confluiscono nella stessa voce di film, come già accade per gli altri
   film su più giorni.
3. Vecchio indirizzo che non rimanda a nessuna pagina film che funziona -> **tenere gli orari senza
   link** (`source_url = None`), mai scartare le proiezioni.
4. I quattro JSON di output già raccolti, con i link rotti dentro -> **ripararli adesso** con la
   stessa regola del fix, così il prossimo `make seed` è pulito senza aspettare la run delle 03:00.

**Meccanismo deciso** (conseguenza diretta delle risposte, non una scelta aperta).
In `_parse_rsc_payload`, un `permalink` che contiene `/extra/` viene **risolto** sul primo
`"permalink"` successivo al match che contiene `/films/` e ha come ultimo segmento lo stesso `slug`
del record. Se non c'è, il record resta con `permalink` vuoto/None: gli orari si tengono, la
descrizione e gli show di dettaglio non si chiedono (le funzioni di dettaglio escono già per
permalink falsy). La risoluzione avviene **prima** della chiave di deduplica, così il record
`/extra/` e il record `/films/` dello stesso film si fondono: show accumulati, `content` più
completo. Le due costanti di route (`_FILMS_ROUTE`, `_EXTRA_ROUTE`) sono costanti di modulo, accanto
ai regex del payload in testa al connettore: nessun secondo file di codice da toccare.

**Criteri di successo**
- `grep -c "postmodernissimo.com/extra/" scraper/output/*.json` restituisce 0 su `showings.json` e
  `movies.json` (e `errors.json` non esiste più).
- Con un payload che contiene record annidati `/extra/` + `/films/`, `scrape()` produce **un** film
  per titolo, con `source_url` sulla pagina `/films/` e nessuna richiesta HTTP verso `/extra/`.
- `make lint` e `make test-scraper` verdi; conteggi dei test dichiarati aggiornati ovunque.

**Esclusioni**
- Non si toccano gli altri connettori, né il contratto JSON (`validate_output.py`, seed backend): la
  forma dei dati non cambia, cambia solo il valore di `source_url`.
- Non si aggiunge un cinema, non si aggiornano dipendenze, non si tocca `NOTICE`.
- `errors.json` (artefatto non tracciato) si ignora e si cancella, non si versiona.

## Passi

- 0. Commit del contratto e del piano | files: docs/briefs/postmod-extra-route/plan.md | done: commit su `main` che contiene solo questo file, albero del resto invariato | Stato: DONE
- 1. Risolvere il permalink `/extra/` sul `/films/` corrispondente nel parser RSC, senza mai chiedere il dettaglio di una route morta | files: scraper/scraper/connectors/postmodernissimo.py | done: `ruff check` + `ruff format --check` verdi; leggi il file e verifica che la risoluzione avvenga prima della chiave di deduplica e che `source_url` resti `None` quando non c'è pagina film | Stato: DONE
- 2. Test di comportamento sul payload annidato: link risolto e una sola voce per film, record senza pagina film tenuto con `source_url` assente, nessuna richiesta HTTP verso `/extra/`, `/eventi/` ancora scartato | files: scraper/tests/test_postmodernissimo.py | done: `python3 -m pytest tests/test_postmodernissimo.py -q` verde con i nuovi test, suite scraper intera verde | Stato: DONE
- 3. Ripulire i JSON di output della run di prova: `source_url` dei due record `/extra/` portato su `/films/<slug>`, via le due voci di errore 404 da `movies.json`, `errors.json` cancellato e messo in `.gitignore` | files: scraper/output/showings.json,scraper/output/movies.json,scraper/output/cinemas.json,scraper/output/films.json,.gitignore | done: `grep -c "postmodernissimo.com/extra/" scraper/output/showings.json scraper/output/movies.json` = 0/0; `git diff --stat` limitato ai quattro fixture rigenerati (`showings.json`, `movies.json`, `cinemas.json`, `films.json`) e a `.gitignore` | Stato: DONE
- 4. Allineare la doc del connettore alla nuova regola: come si risolve il permalink e cosa succede quando la pagina film non c'è, più la verifica in testa | files: docs/scraper/connettori/postmodernissimo.md,docs/scraper/architecture.md | done: le due pagine descrivono la risoluzione `/extra/` -> `/films/` e il caso senza pagina film; intestazione `Verificato su <commit>` aggiornata | Stato: DONE
- 5. Riga di diario e conteggi dei test dichiarati | files: docs/stato-e-diario.md,AGENTS.md,README.md | done: riga in coda a `stato-e-diario.md` datata 2026-11-20 con esito e conteggi reali; ogni "186" ora non più vero è allineato al numero misurato | Stato: DONE
- 6. Review a contesto fresco, tre angoli (correttezza, sicurezza/dati, coerenza col brief) | files: nessuno (sola lettura) | done: P0/P1/P2 con `file:riga` e verdetto merge per angolo | Stato: DONE

## Lanes

- **lane codice** — `scraper/scraper/connectors/postmodernissimo.py` (passo 1, `worker`).
- **lane test** — `scraper/tests/test_postmodernissimo.py` (passo 2, `worker`).
- **lane doc** — `docs/scraper/connettori/postmodernissimo.md`, `docs/scraper/architecture.md`
  (passo 4, `worker`).
- **padre** — passo 0 (commit), passo 3 (dati), passo 5 (diario e conteggi), review (passo 6).
- **shared** — nessuno: codice, test, doc e dati sono file disgiunti. Le lane 1-3 partono insieme in
  una sola ondata; il padre lavora sui JSON mentre loro girano.
