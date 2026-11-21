# Brief + piano — le due voci latenti di PostModernissimo

> Verificato su `fefe097` (`2026-11-21`). Classe `M`, stile `full`.
> Origine: le due voci datate `2026-11-21` in [`problemi-aperti.md`](../../problemi-aperti.md)
> (slug del permalink rotto da query o fragment; nessun guard esplicito su `/extra/` nei lettori
> di dettaglio).

## How to resume

- Albero: `main` pulito su `fefe097`, 0 commit avanti su `origin/main`. Branch di lavoro:
  `fix/scraper-postmod-guard-slug`.
- Gate: `make lint` e `make test-scraper` (Docker, albero pulito richiesto). Atteso dopo i tre test
  nuovi: 196 pass + 1 `xfail` (197 raccolti), totale 292.
- Il blocco 0 e' il commit di questo file: senza di lui non si riparte.
- Primo blocco da eseguire: il primo `Stato: TODO` con condizione vera (`grep '| Stato: TODO'`).
- Trappola: `scraper/scraper/connectors/postmodernissimo.py` ha tre punti che ricavano lo slug con
  `rstrip("/").split("/")[-1]`; il fix li copre tutti e tre (decisione 3b). Nessuno scraping live.

## Obiettivo

Chiudere le due voci latenti del connettore PostModernissimo: lo slug del permalink non deve
rompersi quando l'URL porta una query o un fragment, e nessun lettore di dettaglio deve poter
partire verso la route morta `/extra/` per sola fiducia nel filtro a monte.

## Vincoli

- Un solo file di codice (`scraper/scraper/connectors/postmodernissimo.py`) piu' i test del
  connettore. Nessun cambiamento al contratto JSON, al seed o a `validate_output.py`.
- Nessuno scraping live: i test usano `responses` e payload inline.
- Il guard su `/extra/` e' silenzioso: nessun errore `detail`, perche' non e' un guasto.
- Italiano in commenti, commit, documenti.

## Decisioni chiuse (domanda -> risposta)

1. **I conteggi dei test citati nei documenti (194 scraper, 289 totali)?** Compaiono in `AGENTS.md`
   (2 punti), `README.md`, `docs/panoramica.md` (2 punti) e `docs/development-windows.md` (2 punti):
   aggiungere due test li rende falsi. -> **Si aggiornano in questo ciclo**, nello stesso commit della
   riga di diario (5+ righe, nessuna decisione).
2. **Il blocco su `/extra/` deve lasciare traccia?** -> **Silenzioso**, gemello di `/eventi/`: si
   esce prima della richiesta, senza registrare un errore. `/extra/` e' una route morta nota, non un
   guasto, e la promessa e' solo "mai una GET li'".
3. **Lo stesso difetto dello slug esiste in altri due punti** (sinossi dal payload di dettaglio,
   card HTML della homepage): -> **si correggono tutti e tre** con una funzione condivisa di due
   righe. Una sola regola da tenere giusta; i test restano i due richiesti (uno per difetto).

## Criteri di successo

- I due test nuovi falliscono sul codice pre-fix e passano dopo (verificato con `git stash` o su
  copia del file, non a memoria).
- `make lint` e `make test-scraper` verdi, 197 test scraper raccolti.
- Nessuna occorrenza residua della ricetta `rstrip("/").split("/")[-1]` nel file del connettore.
- Le due voci spariscono da `docs/problemi-aperti.md` (non barrate: cancellate).
- Riga in coda a `docs/stato-e-diario.md`.

## Esclusioni

- Nessun nuovo errore `detail`, nessun nuovo campo nei modelli, nessun refactor del parser.
- Nessun tocco agli altri connettori, alle fixture registrate, al backend o all'app.

## Piano

- 0. Commit del contratto e del piano | files: docs/briefs/postmod-guard-slug/plan.md | done: commit esiste e l'albero e' pulito | Stato: DONE
- 1. Funzione `_url_slug(url)` (via `urlparse(...).path`) e uso nei tre punti: confronto del permalink film, slug bersaglio della sinossi di dettaglio, slug delle card HTML | files: scraper/scraper/connectors/postmodernissimo.py | done: nessun `rstrip("/").split("/")[-1]` residuo nel file; `ruff check` pulito | Stato: DONE
- 2. Guard gemelli di `/eventi/`: `fetch_film_detail` esce con `None` e `_fetch_detail_shows` con `[]` quando l'URL contiene `/extra/`, senza log ne' errore | files: scraper/scraper/connectors/postmodernissimo.py | done: `grep -n "_EXTRA_ROUTE"` mostra quattro occorrenze (costante, parser, due lettori) | Stato: DONE
- 3. Due test rossi-prima-verdi-dopo: slug del permalink con query e con fragment; nessuna richiesta HTTP verso `/extra/` per entrambi i lettori (`responses.calls` vuoto) | files: scraper/tests/test_postmodernissimo.py | done: i due test falliscono sul codice dei blocchi 1-2 assenti e passano; `make test-scraper` -> 196 passed, 1 xfailed | Stato: DONE
- 4. Cancellare le due voci da `docs/problemi-aperti.md` | files: docs/problemi-aperti.md | done: le due intestazioni sullo slug e sul guard non esistono piu'; il resto del file e' intatto | Stato: DONE
- 5. Allineare i conteggi a 197 scraper e 292 totali | files: AGENTS.md,README.md,docs/panoramica.md,docs/development-windows.md | done: `grep -rn "194\|289"` sui documenti vivi non trova piu' i conteggi dei test | Stato: DONE
- 6. Riga di diario della sessione | files: docs/stato-e-diario.md | done: riga in coda con data, fix, conteggi e gate verdi | Stato: DONE
- 7. Gate completi e review a contesto fresco, due angoli (correttezza `deepseek-v4.1-flash`, coerenza col brief `glm-5.3-flash`) | files: docs/briefs/postmod-guard-slug/plan.md | done: `make lint` + `make test-scraper` + `make check-console` verdi, findings P0/P1 chiusi o annotati | Stato: DONE
- 8. Push del branch di lavoro `fix/scraper-postmod-guard-slug` su `origin` | files: nessuno | done: `git status --porcelain` vuoto e branch pubblicato su `origin` | Stato: DONE

## Lanes

- **Lane unica (padre)**: i blocchi 1-6. Il codice e' un file solo (6 righe) e i documenti sono
  allineamenti da una riga; spezzarli su piu' writer costerebbe piu' del lavoro. Nessun `worker`
  figlio.
- **Review (blocco 7, in parallelo)**: due `reviewer` a sola lettura, file disgiunti di sola lettura,
  nessuna scrittura: correttezza (`scraper/scraper/connectors/postmodernissimo.py`,
  `scraper/tests/test_postmodernissimo.py`) e coerenza col brief (stessi file + `docs/`).
- **shared**: nessuno (nessun file condiviso fra padre e review: i reviewer non scrivono).
