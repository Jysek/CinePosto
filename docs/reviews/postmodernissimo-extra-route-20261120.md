# Review — PostModernissimo: route `/extra/` morta

**Verdetto**: `PASS con nits` (zero P0, un P1)
**Stato (2026-11-21)**: P1 (`40464de`) e i cinque P2 applicati — codice e test in `570cbc4`, documenti
allineati nello stesso ciclo. Nessun finding aperto.
**Oggetto**: diff `origin/main...HEAD`, 13 file (5 commit): connettore, test, quattro fixture JSON,
documentazione, `.gitignore`. Patch materializzate in `%TEMP%/cineposto-review-20261120/`.
**Gate**: verde — `make lint` (ruff check + format, scraper e backend) e `make test-scraper`
(`189 passed, 1 xfailed`, 66,97 s). Il primo tentativo è fallito per daemon Docker spento: `gate non
eseguibile`, poi rifatto a daemon attivo.
**Base**: `origin/main` (5 commit, HEAD `6893657`).

```text
$ make lint
All checks passed!
45 files already formatted
All checks passed!
43 files already formatted
$ make test-scraper
........................................................................ [ 75%]
.........................................x....                           [100%]
189 passed, 1 xfailed in 66.97s (0:01:06)
```

## Finding

- P1 | scraper/scraper/connectors/postmodernissimo.py:238-254 | il ramo di fusione per slug non aggiorna mai `permalink` (scritto solo alla prima occorrenza): se la voce `/extra/` precede quella `/films/` dello stesso slug e la risoluzione torna `None`, il permalink buono del record successivo viene scartato e le date escono senza link, pur avendo la pagina film | fix: nel ramo merge `existing["permalink"] = existing.get("permalink") or permalink` | done: test con `/extra/` irrisolto prima e `/films/<stesso slug>` dopo, con `{s.source_url for s in film.present_in} == {_FILMS_PERMALINK}`
- P2 | scraper/scraper/connectors/postmodernissimo.py:266-269 | la finestra di ricerca è un limite fisso di 3000 caratteri senza la guardia sul confine del record che `_extract_content` applica (`text.find('{"id":', start)`): con una sinossi lunga prima dell'oggetto `movie` la ricerca esce dal record e non risolve | fix: fermare la ricerca al primo `{"id":` successivo, non solo al limite di 3000 | done: test con `content` di ~4000 caratteri prima di `movie` annidato, che risolve
- P2 | scraper/tests/test_postmodernissimo.py:209-220 | manca l'ordine inverso (`/films/` prima di `/extra/`) e non si asserisce la descrizione più completa, che il contratto dichiara come effetto della fusione (`pick_fuller_description`) | fix: fixture invertita + assert su `film.description` | done: i due test verdi
- P2 | scraper/tests/test_postmodernissimo.py:226-232 | il caso «senza pagina film» usa lo slug reale `yalla-parkour`, che in produzione ha `/films/yalla-parkour` (prova: nessun 404 su quella URL nella run, `history/movies_2026-11-20.json`) | fix: slug inventato | done: test verde con slug fittizio, nessun riferimento reale
- P2 | docs/briefs/postmod-extra-route/plan.md:71 | il `done:` del passo 3 promette un diff limitato a `showings.json`/`movies.json`/`.gitignore`, ma la run ha rigenerato anche `cinemas.json` e `films.json` | fix: allineare la riga ai quattro fixture | done: i file elencati coincidono con quelli del commit
- P2 | docs/briefs/postmod-extra-route/plan.md:53-55 | il «Meccanismo deciso» dice le costanti di route «accanto a `_EVENT_HINTS`», che è attributo di classe, mentre nel codice sono costanti di modulo accanto ai regex | fix: una parola nel brief | done: il testo combacia col posizionamento reale

## Verificato senza rilievi

- `.gitignore:72`: `scraper/output/errors.json` è ancorato; nessun pattern generico copre le fixture
  JSON versionate, e nessun test o documento consuma `errors.json` committato.
- Fixture: 39 film in `movies.json` come nella run precedente, nessuna scheda o proiezione persa,
  «Prince of Broadway» una sola voce con 23/11 e 24/11 e sinossi intera, `errors` vuoto, nessun
  `source_url` nullo, nessun segreto nei quattro file.
- Le due URL riparate a mano erano già pagine vive nella stessa run: gli unici due 404 registrati
  erano quelli su `/extra/`.
- Decisioni del contratto e documentazione: le quattro scelte chiuse corrispondono al codice di
  oggi; nessun documento descrive codice inesistente; conteggi coerenti (`190` scraper di cui un
  `xfail`, `285` totali con `95` backend).

Applica: `/ship applica i P0/P1 di docs/reviews/postmodernissimo-extra-route-20261120.md`
