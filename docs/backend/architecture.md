# Backend — Architettura tecnica

> Verificato su `9dc8fc1` (`2026-09-23`).

Vedi setup e avvio in [backend/README.md](../../backend/README.md).
Per le decisioni di design e il quadro d'insieme vedi [panoramica.md](../panoramica.md).
Per il mapping JSON scraper → DB vedi [schema-mapping.md](schema-mapping.md).

---

## Architettura a strati

```
routers/       ← PRESENTATION: riceve HTTP, valida input con Pydantic, chiama services
services/      ← BUSINESS: orchestrazione, regole di dominio
repositories/  ← DATA ACCESS: query SQLAlchemy, nessuna logica di business
models/        ← DOMAIN: entità SQLAlchemy persistite su SQLite
schemas/       ← DTO Pydantic: validazione input/output API (distinti dai modelli ORM)
```

Regola: ogni layer chiama solo il layer immediatamente sotto. Niente skip.

---

## Modello dati (lingua: inglese — decisione L1+L2)

### Cinema (`cinemas`)
PK = **`slug`** (stringa), allineato a `cinemas.json[*].slug` dello scraper.

```
slug        PK string       "postmodernissimo"
name        string NOT NULL
city        string NOT NULL
address     string NOT NULL
region      string default "Umbria"
lat         float NOT NULL
lon         float NOT NULL
website     string nullable
phone       string nullable
```

### Film (`films`)
PK = **`id` intera autoincrement**. Dedup tramite `UNIQUE(title_normalized, year)`.

```
id                INTEGER PK AUTOINCREMENT
title             string NOT NULL
title_normalized  string NOT NULL                  -- lower, no punctuation, single spaces
original_title    string nullable
year              int nullable
runtime_minutes   int nullable
genres            string nullable                   -- CSV
director          string nullable
poster_url        string nullable
synopsis          text nullable
wikidata_id       string nullable UNIQUE            -- arricchimento Wikidata (D1)
created_at        datetime default now
removed_at        datetime nullable                 -- archiviazione (soft delete), vedi «Seed»

UNIQUE(title_normalized, year)
INDEX  ix_film_title_normalized
```

> **Perché PK intera invece di stringa**: il titolo è fragile (em-dash, apostrofi, encoding) e può essere riutilizzato per remake (`Dune 1984` vs `Dune 2021`). PK artificiale + chiave naturale UNIQUE è il pattern standard.

> **Come si incontra la chiave naturale** (`get_by_natural_key` in `film_repo.py`): il titolo si
> normalizza con `normalize_title()` — lowercase, accenti rimossi, punteggiatura → spazio e
> **`&` → `e`** (UCI scrive `AMORI & INCANTESIMI 2`, The Space `Amori e incantesimi 2`: senza
> questa regola la stessa opera cade su due righe). Un `year` NULL è **jolly solo se il candidato
> è unico**: incontra l'anno valorizzato e lo adotta (la riga si completa, non si duplica); se i
> candidati con lo stesso titolo sono più di uno — remake omonimi — non si inventa nulla.
> ⚠️ In SQL `NULL ≠ NULL`: la UNIQUE da sola non blocca i duplicati con anno NULL, è il lookup
> applicativo a garantire la dedup. I doppioni creati prima di queste regole si fondono con lo
> script di manutenzione (vedi «Manutenzione» qui sotto).

### Showing (`showings`)
FK su `Film` (intera) e `Cinema` (slug stringa).

```
id            INTEGER PK AUTOINCREMENT
film_id       int  FK → films.id          ON DELETE CASCADE
cinema_slug   str  FK → cinemas.slug      ON DELETE CASCADE
date          date NOT NULL
times         string NOT NULL              -- JSON array '["18:30","21:00"]'
language      string nullable              -- "ITA"/"ENG"/"ORIG-SUB"
screen        string nullable
buy_url       string nullable              -- source_url nel JSON scraper
scraped_at    datetime default now
removed_at    datetime nullable             -- archiviazione (soft delete), vedi «Seed»

UNIQUE(film_id, cinema_slug, date)
INDEX  ix_showings_date, ix_showings_film, ix_showings_cinema
```

---

## Endpoint

| Metodo | Path | Descrizione |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe (fuori dal prefisso `/api/v1`) |
| `GET`  | `/api/v1/cinema` | Lista cinema |
| `GET`  | `/api/v1/cinema/{slug}` | Dettaglio cinema + conteggio showings |
| `GET`  | `/api/v1/cinema/{slug}/showings?date_from&date_to` | Programmazione del cinema |
| `GET`  | `/api/v1/film/oggi` | Film con almeno uno showing oggi |
| `GET`  | `/api/v1/film/settimana` | Film in programmazione oggi → +7 giorni |
| `GET`  | `/api/v1/film/search?q=...&limit=...` | Ricerca per titolo (min 2 caratteri) |
| `GET`  | `/api/v1/film/{film_id}` | Dettaglio film + prossimi showings |
| `GET`  | `/api/v1/showings?date=YYYY-MM-DD` | Spettacoli di una data (default: oggi) |
| `POST` | `/api/v1/admin/reimport` | Rilegge JSON scraper (header `X-Admin-Token` richiesto) |
| `GET`  | `/api/v1/admin/dataset-info` | Conteggi e ultima data dataset (protetto) |

Tutti gli endpoint sono **sola lettura** salvo `/admin/reimport`. I dati arrivano dallo scraper, non da utenti.
Il contratto autorevole (URL, query params, forma delle risposte, codici HTTP) è [api.md](api.md).

---

## Seed da JSON scraper

I JSON dello scraper sono **single source of truth**. Il backend li legge e li importa nel DB.

```
scraper/output/cinemas.json  → tabella cinemas
scraper/output/films.json    → tabella films
scraper/output/showings.json → tabella showings
```

**Ordine di esecuzione obbligatorio** (vincoli FK):
1. cinemas → upsert per slug
2. films → upsert per (title_normalized, year); costruisci lookup `{titolo_stringa_JSON: id_intera_DB}`
3. showings → usa lookup per risolvere `film_id` intera; upsert per (film_id, cinema_slug, date)
4. riconciliazione → le righe non più nei JSON dell'ultima importazione si **archiviano**
   (`removed_at`), quelle che ricompaiono si riattivano. **Mai `DELETE`**: il DB conserva lo storico.

La riconciliazione (finestra coperta dai JSON, guardia anti-fonte-rotta per cinema, report
`archived_*`/`reactivated_*`/`skipped_cinemas`) è descritta in [schema-mapping.md](schema-mapping.md)
§4.1. Le query pubbliche filtrano `removed_at IS NULL`: i film archiviati e i loro spettacoli non
compaiono nell'API. Interruttori in config: `seed_archive_enabled`, `seed_archive_min_ratio`.

Specifica completa in [schema-mapping.md](schema-mapping.md).

**Trigger del seed**:
- **Manualmente**: script `python -m app.seed_from_json` (al primo deploy / fix locale).
- **Periodicamente**: `cron` esterno o `systemd timer` invoca `POST /api/v1/admin/reimport` dopo che lo scraper ha aggiornato i JSON.

Nessuno scheduler interno al backend (decisione D2): lo scraper vive nel suo processo via systemd timer separato (vedi `scraper/deploy/cineposto-scraper.timer`).

---

## Manutenzione: fusione dei doppioni

Il seed non cancella: con le run accumulate possono restare **due righe per lo stesso film**
(titolo scritto diversamente, anno NULL). Le righe non più in programmazione il seed le **archivia**
(`removed_at`), ma due doppioni *entrambi* vivi restano da unire a mano — lo script di manutenzione le
fonde in modo controllato:

```bash
docker compose run --rm backend python -m app.maintenance.dedup_films               # DRY-RUN + report
docker compose run --rm backend python -m app.maintenance.dedup_films --apply       # applica
docker compose run --rm backend python -m app.maintenance.dedup_films --merge 40:52 # fusione approvata a mano
```

Regole (tutte esplicite, mai «assomiglia un po'»):

- **dry-run di default**: senza `--apply` stampa solo il piano, non scrive nulla;
- **gruppi certi**: stessa chiave ricalcolata (anno uguale, oppure NULL che adotta l'anno
  valorizzato), stesso `wikidata_id`, coppia indicata con `--merge`. Conflitti evidenti (es.
  `wikidata_id` diversi) → gruppo **«da decidere»**, nessuna fusione;
- **superstite deterministico**: più showings → anno valorizzato → `wikidata_id` → più metadati →
  id più basso. I campi NULL del superstite si completano da ciò che si fonde;
- **collisioni di showings**: per `(cinema_slug, date)` vince la run con `scraped_at` più recente,
  l'altra riga viene scartata e il report elenca gli orari persi;
- **candidati solo segnalati**: titoli simili (edit distance ≤ 2, o uno è l'altro più un suffisso di
  parole) compaiono nel report ma **non si fondono**: servono `--merge`, uno per volta;
- **una transazione sola** con `--apply`, rollback su eccezione, idempotente (seconda passata =
  0 gruppi).

I titoli italiani completamente diversi per lo stesso film (es. `CARS - MOTORI RUGGENTI - 20MO
ANNIVERSARIO` vs `Cars – 20esimo anniversario`) non ricadono in nessuna regola: restano da unire a
valle, con `--merge` manuale o con un merge cross-fonte nello scraper.

---

## Tecnologie

| Cosa | Scelta | Motivo |
|------|--------|--------|
| Framework | FastAPI | Async, Pydantic integrato, Swagger auto |
| ORM | SQLAlchemy 2.0 sync | Sufficiente per la scala, più semplice di async |
| DB dev + prod | **SQLite** (D4) | Bassa concorrenza, lettura-pesante, zero ops |
| Migrations | **nessun tool (niente Alembic)** | Le tabelle nascono con `Base.metadata.create_all` nel lifespan; le colonne nuove arrivano con un `ALTER TABLE` idempotente (`app/maintenance/migrate_removed_at.py`), perché il DB contiene storico e non si ricrea dal seed. Alembic va introdotto solo quando il DB non sarà più ricreabile (regola di `AGENTS.md`) |
| Arricchimento dati | **Wikidata via scraper** (D1) | Già fatto a monte, gratis, niente API key |
| Scheduling | **Esterno** (systemd timer + `--once`) (D2/L3) | Backend resta stateless rispetto allo scraping |
| Identità Cinema | **PK slug stringa** (D3) | Allineato JSON, URL parlanti |
| Identità Film | **PK intera + UNIQUE(title_normalized, year)** (D3) | Robusto a remake e encoding fragile; il match applicativo fonde `&`/`e` e adotta l'anno NULL |
| Lingua codice/schema | **Inglese** (L1+L2) | Allineato JSON scraper, niente traduzione runtime |
| Sicurezza endpoint admin | Header `X-Admin-Token` | Sufficiente per MVP locale; in prod aggiungere HTTPS + IP allowlist |
