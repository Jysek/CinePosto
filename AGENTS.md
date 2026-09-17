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
app/       Expo SDK 54 / React Native (web + iOS + Android dalla stessa codebase)
docs/      documentazione tecnica (in italiano)
```

## Comandi canonici

L'ambiente primario è **Docker** (funziona uguale su Windows e macOS, e non richiede Python locale):

| Cosa | Comando |
|---|---|
| Avvia il backend | `make up` |
| Test backend (26) | `make test` |
| Test scraper (75) | `make test-scraper` |
| Lint | `make lint` |
| Seed DB dai JSON | `make seed` |
| Scraping live (con parsimonia) | `make scrape` |
| Aiuto completo | `make help` |

Ogni target stampa il comando `docker compose` equivalente: il Makefile è una scorciatoia.
Setup completo (Docker, telefono, firewall, IP di rete) in
[`docs/development-windows.md`](docs/development-windows.md).

Senza Docker (fallback, richiede Python 3.12 locale), dal componente giusto:

| Cosa | Comando |
|---|---|
| Test scraper | `python3 -m pytest tests/ -q` (75 test) |
| Lint scraper | `python3 -m ruff check scraper/ tests/` |
| Run scraper (una volta) | `python3 -m scraper.main --once` |
| Test backend | `python -m pytest tests/ -q` (26 test) |
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

## Definition of done

Una modifica non è finita finché:

1. `ruff check` passa su scraper e backend;
2. i test del componente passano (`pytest`), e i test nuovi **descrivono il comportamento**
   (`test_returns_empty_list_when_no_showings`, non `test1`);
3. la CI (`.github/workflows/ci.yml`) resta verde;
4. se cambia un contratto (JSON o API), sono aggiornati anche il consumatore e i documenti;
5. nessun segreto, nessun `.env`, nessun `.db`, nessun output di cache finisce nel commit.

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

`docs/iss/**`, `docs/presentazione-14-luglio.*`, `docs/esposizione-discorsi.*` sono il
**materiale d'esame del 14 luglio 2026**: archivio storico, non si modifica (al massimo una
nota in testa se diverge dalla realtà). La documentazione viva è `docs/panoramica.md` +
`docs/<area>/architecture.md`, più `docs/development-windows.md` per il setup locale.

## Cosa non fare

- Non aggiornare le dipendenze "per pulizia" mentre si lavora a una feature.
- Non introdurre Alembic finché il DB è ricreabile dal seed.
- Non aggiungere un cinema senza voce nel registro di copertura e test del connettore.
- Non modificare file del materiale d'esame.
- Non fare `git push --force` sul repo pubblico.
