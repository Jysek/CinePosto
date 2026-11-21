# Brief + piano — P2 della review PostModernissimo `/extra/`

> Verificato su `359b763` (`2026-11-21`). Classe `M`, stile `full`.
> Origine: [review](../../reviews/postmodernissimo-extra-route-20261120.md), i sei P2 (il P1 e' gia' in
> `main` con `40464de`).

## Obiettivo

Chiudere i P2 della review: la ricerca del permalink `/films/` dentro un record `/extra/` non deve
dipendere da una finestra fissa di caratteri, e i test devono coprire anche l'ordine inverso dei
record e il caso "senza pagina film" senza usare lo slug reale di un film in produzione. I due P2
sul brief storico si allineano al codice e alla run che e' realmente avvenuta.

## Vincoli

- Solo `scraper/` lato codice, nessuna modifica al contratto JSON, al seed, a `validate_output.py`.
- Nessuno scraping live: i test usano `responses` e fixture inline.
- Nessuna rinomina, nessun refactor fuori dai quattro P2.
- Italiano in commenti, commit, documenti.

## Decisioni chiuse (domanda -> risposta)

1. **Come si limita la ricerca del permalink?** La review suggerisce "fermati al primo `{"id":`".
   Il fatto lo smentisce: l'oggetto `movie` annidato **comincia** con `{"id":`, quindi quella guardia
   ucciderebbe proprio il caso che il `done:` della review pretende risolto (sinossi di ~4000 char
   prima di `movie`). -> **Si limita la ricerca all'oggetto record stesso**, individuato con
   brace-matching da `start` (stessa tecnica gia' usata da `_extract_details`/`_extract_shows`), con
   tetto `_RECORD_SCAN_LIMIT = 20000` per payload malformati.
2. **Si deduplica il brace-matching gia' duplicato in `_extract_details`/`_extract_shows`?**
   No: due chiamanti non sono una ripetizione reale, e toccarli cambierebbe il loro
   comportamento. -> helper nuovo usato solo dalla risoluzione.
3. **Il test `unresolved_extra_record_takes_permalink_from_later_film_record` perde senso?**
   No: cambia solo il motivo per cui la risoluzione torna `None` (il record non porta la pagina
   film, non "sta oltre 3000 caratteri"). Il commento va riscritto, l'asserzione resta.
4. **Lo slug reale `yalla-parkour` nel test "senza pagina film"?** -> slug e titolo inventati
   (`documentario-senza-pagina`), nessun riferimento a un film reale, sentinella `responses`
   allineata.
5. **Conteggi dei test**: due test nuovi -> 193 scraper (192 pass + 1 `xfail`), 288 totali.

## Criteri di successo

- Test nuovo: record `/extra/` con sinossi di ~4000 caratteri prima dell'oggetto `movie` annidato ->
  `source_url` e' la pagina `/films/`, e la pagina film viene interrogata.
- Test nuovo: record `/films/` **prima** di quello `/extra/` dello stesso slug -> un solo film, date
  di entrambi, `description` e' la variante piu' completa.
- Il test "senza pagina film" non nomina piu' `yalla-parkour`.
- `docs/briefs/postmod-extra-route/plan.md` non contraddice ne' il codice (posizione delle costanti)
  ne' i file realmente toccati dalla run (quattro fixture JSON).
- `make lint` e `make test-scraper` verdi; ogni conteggio dichiarato nei documenti e' quello
  misurato.

## Esclusioni

- Non si tocca il contratto JSON, i fixture di `scraper/output/`, il backend, l'app.
- Non si tocca `NOTICE`, il materiale d'esame, `.env*`, la CI.
- Non si riscrive la review: solo la riga di stato in testa.

## Passi

- 0. Commit del contratto e del piano | files: docs/briefs/postmod-extra-route-p2/plan.md | done: commit su `main` che contiene solo questo file | Stato: TODO
- 1. La risoluzione del permalink cerca dentro il record, non entro 3000 caratteri fissi: `_record_end` con brace-matching e tetto `_RECORD_SCAN_LIMIT`, usata da `_resolve_film_permalink` | files: scraper/scraper/connectors/postmodernissimo.py | done: `ruff check` + `ruff format --check` verdi; il test esistente del caso irrisolto resta verde | Stato: TODO
- 2. Test: sinossi lunga prima di `movie` annidato che risolve; ordine inverso `/films/` poi `/extra/` con assert su `description` piu' completa; slug inventato nel caso "senza pagina film"; commento del test "irrisolto" allineato al nuovo motivo | files: scraper/tests/test_postmodernissimo.py | done: `python -m pytest tests/ -q` da `scraper/` -> 192 passed, 1 xfailed | Stato: TODO
- 3. Scheda connettore: §3 dice che la ricerca sta dentro il record (non "entro 3000 char"), §8 elenca i due test nuovi, intestazione `Verificato su <commit>` aggiornata al commit del passo 1 | files: docs/scraper/connettori/postmodernissimo.md | done: nessuna riga della scheda descrive una finestra fissa per il permalink | Stato: TODO
- 4. Brief storico allineato ai fatti: il `done:` del passo 3 nomina i quattro fixture, il "Meccanismo deciso" dice che le costanti di route sono di modulo accanto ai regex (non "accanto a `_EVENT_HINTS`") | files: docs/briefs/postmod-extra-route/plan.md | done: `grep -n "_EVENT_HINTS" docs/briefs/postmod-extra-route/plan.md` vuoto; la riga dei file elenca i quattro fixture | Stato: TODO
- 5. Conteggi reali nei documenti: 191 -> 193 scraper, 286 -> 288 totali | files: AGENTS.md,README.md,docs/panoramica.md,docs/development-windows.md | done: `grep -rn "191\|286" AGENTS.md README.md docs/ | grep -v stato-e-diario` vuoto | Stato: TODO
- 6. Riga di stato nella review e riga di diario della sessione | files: docs/reviews/postmodernissimo-extra-route-20261120.md,docs/stato-e-diario.md | done: la review dichiara i P2 applicati con i `file:riga` risolti; il diario ha la riga datata con esito, conteggi e gate | Stato: TODO
- 7. Gate completo e push sul branch di lavoro | files: nessuno (sola lettura + git) | done: `make lint`, `make test-scraper`, `make check-console` verdi; albero pulito; push su `origin` del branch | Stato: TODO

## Lanes

- **lane codice** — `scraper/scraper/connectors/postmodernissimo.py` (passo 1, `worker`).
- **lane test** — `scraper/tests/test_postmodernissimo.py` (passo 2, `worker`). Scrive i test sul
  contratto del passo 1: rosso finche' il codice non atterra, verde a fine ondata.
- **lane doc** — `docs/scraper/connettori/postmodernissimo.md`, `docs/briefs/postmod-extra-route/plan.md`
  (passi 3-4, `worker`; l'intestazione `Verificato su` usa lo sha del passo 1, che il padre gli passa).
- **padre** — passo 0 (commit), passo 5 (conteggi, dopo il verdetto dei test), passo 6 (review e
  diario), passo 7 (gate e push), commit a confini logici.
- **shared** — nessuno: codice, test e documenti sono file disgiunti.

## How to resume

- Gate del repo: `make lint` e `make test-scraper` (Docker); fallback nativo da `scraper/`:
  `python -m pytest tests/ -q` e `python -m ruff check scraper/ tests/`.
- Prima di ogni blocco: `git status --porcelain` deve essere vuoto; i commit si fanno per path.
- Trappola d'ambiente: il primo tentativo della sessione precedente falli' per daemon Docker spento
  -> "gate non eseguibile", non un difetto di codice.
- Trappola d'ambiente: `responses` + payload RSC si costruiscono con `_build_rsc_push`; l'ordine dei
  dict nella fixture e' l'ordine nel payload, quindi i test sull'ordine dei record dipendono da
  quello.
- Trappola d'ambiente: l'unescape del payload (`\"` -> `"`) rende le stringhe JSON non valide: il
  brace-matching dei confini e' naive, come negli helper esistenti.
- Primo blocco da eseguire: passo 1 (codice), poi ondata con test e doc.
- Stato da interrogare: `grep '| Stato: TODO' docs/briefs/postmod-extra-route-p2/plan.md`.
