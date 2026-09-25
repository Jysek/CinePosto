# AGENTS.md — CinePosto

Istruzioni di progetto per l'agente (Pi). Integra le regole globali in `~/.pi/agent/AGENTS.md`:
quelle valgono sempre, queste sono specifiche di CinePosto.

## Cos'è

Aggregatore della programmazione dei cinema dell'Umbria: uno scraper Python raccoglie
i palinsesti, un backend FastAPI li serve via REST, un'app React Native (Expo) li mostra
su web e mobile. Nessuna registrazione utente.

Monorepo a quattro pezzi indipendenti collegati da contratti espliciti (**file JSON** tra
scraper e backend, **API REST** tra backend e app):

```
scraper/   pipeline Python 3.12 → JSON in scraper/output/
backend/   FastAPI + SQLAlchemy + SQLite (seed dai JSON)
app/       Expo SDK 57 / React Native 0.86 (web + iOS + Android dalla stessa codebase)
docs/      documentazione tecnica (in italiano)
```

## Comandi canonici

L'ambiente primario è **Docker** (funziona uguale su Windows e macOS, e non richiede Python locale):

| Cosa | Comando |
|---|---|
| Avvia tutto (Docker + backend + app) | `make dev` |
| Avvia il backend | `make up` |
| Test backend (60) | `make test` |
| Test scraper (173) | `make test-scraper` |
| Lint | `make lint` |
| Messaggi di console ASCII | `make check-console` |
| Seed DB dai JSON | `make seed` |
| Scraping live (con parsimonia) | `make scrape` |
| Aiuto completo | `make help` |

Ogni target stampa il comando `docker compose` equivalente: il Makefile è una scorciatoia.
Setup completo (Docker, telefono, firewall, IP di rete) in
[`docs/development-windows.md`](docs/development-windows.md).

Senza Docker (fallback, richiede Python 3.12 locale), dal componente giusto:

| Cosa | Comando |
|---|---|
| Test scraper | `python3 -m pytest tests/ -q` (173 test) |
| Lint scraper | `python3 -m ruff check scraper/ tests/` e `python3 -m ruff format --check scraper/ tests/` |
| Run scraper (una volta) | `python3 -m scraper.main --once` |
| Test backend | `python -m pytest tests/ -q` (60 test) |
| Seed DB dai JSON | `python -m app.seed_from_json` |
| Avvio backend | `uvicorn app.main:app --reload --port 8000` |
| App: web | `npx expo start --web` |
| App: export statico | `npx expo export --platform web` |

## Regole di architettura

**Backend — layering stretto** (Sommerville §6.3): `routers/` → `services/` → `repositories/`
→ `models/`. Un layer chiama **solo** quello sotto. Mai query nel router, mai SQL nel service.

**Scraper — un connettore per cinema** (pattern Strategy): ogni cinema implementa
`BaseConnector` (`cinema_name`, `cinema_slug`, `scrape`). `scrape()` **non solleva** per
errori di rete/parsing: li raccoglie in `ScrapeResult.errors`, così una fonte rotta non
blocca le altre. Le costanti del cinema vivono in `scraper/scraper/config.py`.

**App** — i dati dei cinema arrivano dall'API, non da costanti hardcoded: aggiungere un
cinema non deve richiedere un rebuild dell'app.

**Contratti** — se cambi la forma dei JSON prodotti dallo scraper, aggiorna il seed del
backend e `validate_output.py` nello stesso commit.

## Convenzioni

- Lingua: **italiano** nei messaggi di commit, nei commenti e nella documentazione.
- Commit: `<tipo>: <descrizione>` oppure `<tipo>(<scope>): <descrizione>` con scope
  `scraper` / `backend` / `app` / `docs` / `ci`. Tipi: `feat`, `fix`, `refactor`, `docs`,
  `test`, `chore`, `perf`. Atomic: una modifica logica per commit.
- Nomi: `camelCase` per variabili/funzioni (Python: `snake_case`), `PascalCase` per classi
  e componenti, `UPPER_SNAKE_CASE` per le costanti, `normalize_title()` / `films_today()`
  per le funzioni pure.
- Funzioni sotto le ~50 righe, un solo compito, return anticipati.
- Niente magic number: soglie, timeout e limiti vanno in `config.py` (o costanti nominate).
- Codice commentato in italiano **spiegando il perché**, non il cosa.

## Confini — cosa non si tocca mai

Il progetto è interamente mio, quindi non ci sono confini di giurisdizione. Restano i confini di
sicurezza e di rispetto verso le fonti:

- `.env`, `.env.prod` e ogni loro variante: contengono segreti, si modificano solo a mano e mai
  da un agente.
- `data/**` e `backend/data/*`: dati e database di produzione.
- `docs/iss/**`, `docs/presentazione-14-luglio.*`, `docs/esposizione-discorsi.*`: materiale
  d'esame del 14 luglio 2026. Archivio storico, non si modifica (al massimo una nota in testa se
  diverge dalla realtà).
- `NOTICE`: dichiara i vincoli etici dello scraping. Si modifica solo su richiesta esplicita.
- `.github/workflows/ci.yml`: si modifica solo se fa parte del task in corso.
- **Scraping live** (`make scrape`): si esegue solo su richiesta esplicita, mai "per controllare",
  mai in loop. È una promessa fatta ai cinema.

## Definition of done

Una modifica non è finita finché:

1. `ruff check` e `ruff format --check` passano su scraper e backend (`make lint`);
2. i test del componente passano (`make test` / `make test-scraper`), e i test nuovi
   **descrivono il comportamento** (`test_returns_empty_list_when_no_showings`, non `test1`);
3. per l'app passano `npx expo-doctor` e l'export web (`make check-app-web`);
4. la CI (`.github/workflows/ci.yml`) resta verde;
5. se cambia un contratto (JSON o API), sono aggiornati **nello stesso commit** il consumatore,
   `validate_output.py` e i documenti;
6. **`docs/` è aggiornato**: un lettore che apre solo `docs/index.md` capisce cosa fa oggi il
   progetto, e in coda a `docs/stato-e-diario.md` c'è la riga di questa sessione;
7. nessun segreto, nessun `.env`, nessun `.db`, nessuna cache finisce nel commit.

Un lavoro con i documenti disallineati **non è finito**, anche se test e CI sono verdi.

## Scraper: vincoli non negoziabili

Il progetto fa scraping etico e lo dichiara in `NOTICE`:

- rispetto di `robots.txt`, rate limiting, una run al giorno (03:00 su timer systemd);
- **User-Agent identificabile** con repository e contatto reale — oggi
  `CinePosto/1.0 (+https://github.com/Jysek/CinePosto; 55837328+Jysek@users.noreply.github.com)`;
- i dati raccolti sono informazioni pubbliche di programmazione, uso non commerciale,
  poster e sinossi linkati e non ridistribuiti;
- se una sala chiede di essere rimossa, la si rimuove.

In sviluppo **non** lanciare lo scraping live a ripetizione: usa i JSON committati come
fixture e lascia il live a run esplicite e motivate.

## Sicurezza e segreti

- `.env` non è versionato; i segreti stanno lì e solo lì (`.env.example` documenta le chiavi).
- `ADMIN_TOKEN` protegge `POST /api/v1/admin/reimport`: mai un valore banale, mai in chiaro nei log.
- `CORS_ORIGINS` deve restare una lista esplicita di origin, non `*`.
- Validazione dell'input al confine (routers, lettura JSON).

## Documentazione

La documentazione sta in `docs/` ed è **la fonte di verità di cosa il progetto è oggi**.
È versionata nel repository: si aggiorna con un commit, come il codice. `docs/index.md` è
l'unico ingresso.

Ruoli, senza duplicazioni:

- `AGENTS.md` (questo file) = regole e vincoli. Non ripete il contenuto tecnico.
- `docs/` = documentazione completa del progetto. Racconta lo stato di oggi, non la storia.
- `README.md` = vetrina breve per chi arriva: cosa fa il progetto e come si avvia. Non è la
  documentazione.

Regole di manutenzione:

1. **Stesso commit**: chi cambia il comportamento aggiorna `docs/` nello stesso commit. Codice e
   documento viaggiano insieme.
2. **Refactor interno senza cambio di comportamento**: non riscrive i capitoli, aggiunge solo la
   riga di diario.
3. **Un problema risolto si cancella** da `docs/problemi-aperti.md`. Non si annota "risolto il…",
   non si lascia la voce barrata: la riga sparisce.
4. **Codice o feature rimossi**: il capitolo che li descrive si riscrive o si elimina. Mai
   documentazione che descrive codice inesistente.
5. **Niente cronologia dentro i capitoli**: nessun "prima era così". Lo stato è quello di oggi; la
   storia sta solo in `docs/stato-e-diario.md`.
6. **Intestazione di verifica**: ogni documento vivo dichiara in testa
   `> Verificato su <commit> (<data>).` Se un capitolo è vecchio rispetto a `main`, va riletto
   prima di fidarsene.

| Cosa hai toccato | Dove aggiorni in `docs/` |
|---|---|
| Connettore scraper, normalizzazione titoli, `config.py` | `scraper/architecture.md` + `scraper/copertura.md` + `scraper/connettori/<sala>.md` |
| Forma dei JSON prodotti dallo scraper | `backend/schema-mapping.md` + seed del backend + `validate_output.py` (stesso commit) |
| `routers/`, `services/`, `repositories/`, `models/` | `backend/architecture.md` + `backend/api.md` |
| Endpoint nuovo, cambiato o rimosso | `backend/api.md` (+ `panoramica.md` se cambia il flusso dei dati) |
| Tabella o modello del DB | `backend/schema-mapping.md` + `backend/architecture.md` |
| Schermata, navigazione o client API dell'app | `app/overview.md` |
| Comandi `make`, Docker, variabili d'ambiente | `development.md` + `development-windows.md` + §Comandi canonici di questo file |
| Deploy, Caddy, timer systemd, backup | `deploy.md` |
| Problema nuovo trovato | voce in `problemi-aperti.md` con prova (`file:riga`, comando, esito) e data |
| Problema risolto | **cancella** la voce da `problemi-aperti.md` |
| Feature conclusa, blocco, decisione presa | una riga in coda a `stato-e-diario.md` (append-only) |
| Nuovo file o cartella dentro `docs/` | `docs/index.md` |
| Qualsiasi sessione che tocca codice | **obbligatoria** la riga in `stato-e-diario.md` |

Il materiale d'esame (`docs/iss/**`, `docs/presentazione-14-luglio.*`,
`docs/esposizione-discorsi.*`) è archivio: non si aggiorna e non entra nella tabella qui sopra.

**La doc segue il codice, non il contrario.** Se una pagina di `docs/` contraddice il codice, vince
il codice e la pagina si corregge. Non piegare mai l'implementazione per far tornare i conti con
una pagina vecchia.

## Consegna — git

- **Trunk**: `main`. I branch di lavoro sono brevi, con nome `<tipo>/<scope>-<slug>`
  (esempio: `chore/app-sdk-57`), e confluiscono in `main` appena pronti.
- **Commit**: atomici, una modifica logica per commit, messaggio in italiano
  `<tipo>: <descrizione>` con scope `scraper` / `backend` / `app` / `docs` / `ci`.
- **Push**: consentito su `origin` (repository personale). Sul remote `upstream` (repository di
  gruppo di origine) **non si pusha mai**.
- **CI**: deve essere verde prima del push. È una rete di sicurezza, non un passaggio formale.
- **Pull request**: facoltative. Progetto personale: il merge diretto in `main` è sufficiente.
- **Mai `--force`**, mai `amend` su un commit già pubblicato.

## Cosa non fare

- Non aggiornare le dipendenze "per pulizia" mentre si lavora a una feature.
- Non introdurre Alembic finché il DB è ricreabile dal seed.
- Non aggiungere un cinema senza voce nel registro di copertura e test del connettore.
- Non modificare file del materiale d'esame.
- Non fare `git push --force` sul repo pubblico.
