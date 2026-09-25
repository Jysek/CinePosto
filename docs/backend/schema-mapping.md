# Schema mapping — JSON scraper → DB backend

> Verificato su `a360d5a` (`2026-09-25`): colonne `removed_at` e §4.1 (riconciliazione con
> archiviazione). Il resto del capitolo non è stato ricontrollato in questa sessione.

> **Riferimento autorevole** per lo script di seed e per qualsiasi futura modifica al mapping.
> Allineato alle decisioni L1-L5 e D1-D5 (tabella in [`panoramica.md`](../panoramica.md) §6).

---

## Premessa

Schema completamente in **inglese** (decisione L1+L2): tabelle DB e chiavi JSON usano gli stessi nomi. Niente traduzione runtime.

| Lato | Lingua | Esempio |
|------|--------|---------|
| Scraper JSON output | inglese | `films`, `showings`, `cinemas`, `title`, `year` |
| Backend DB / ORM | inglese | `films` (tabella), `Showing` (classe), `title`, `year` |
| Commenti nel codice | italiano | `# Lookup titolo→id intera per il seed` |

---

## 1. `cinemas.json` → tabella `cinemas`

**File**: `scraper/output/cinemas.json`
**Struttura JSON**:

```json
{
  "generated_at": "2026-06-25T12:56:35.086878+02:00",
  "cinemas": [
    {
      "slug": "postmodernissimo",
      "name": "PostModernissimo",
      "address": "Via del Carmine 4, 06121 Perugia PG",
      "city": "Perugia",
      "region": "Umbria",
      "lat": 43.1129,
      "lon": 12.3933,
      "website": "https://www.postmodernissimo.com"
    },
    ...
  ]
}
```

**Mapping** (1:1, nessuna traduzione):

| JSON | DB column | Note |
|------|-----------|------|
| `slug` | `slug` (PK) | Chiave primaria |
| `name` | `name` | |
| `address` | `address` | |
| `city` | `city` | |
| `region` | `region` | default `"Umbria"` se mancante |
| `lat` | `lat` | float |
| `lon` | `lon` | float |
| `website` | `website` | nullable |
| — | `phone` | non presente nel JSON; sempre null al seed |

**Strategia seed**: per ogni record nel JSON → `cinema_repo.upsert(data)` (SELECT by slug, UPDATE o INSERT).

---

## 2. `films.json` → tabella `films`

**File**: `scraper/output/films.json`
**Struttura JSON**:

```json
{
  "generated_at": "2026-06-25T12:56:35.080884+02:00",
  "films": [
    {
      "id": "Ricchi…da morire - Delitti in famiglia",
      "title": "Ricchi…da morire – Delitti in famiglia",
      "title_normalized": "Ricchi…da morire - Delitti in famiglia",
      "original_title": null,
      "poster": "https://...",
      "description": "Trama...",
      "year": 2026,
      "duration": "95 min",
      "genres": ["Commedia"],
      "director": "Nome Regista",
      "wikidata_id": "Q123456"
    },
    ...
  ]
}
```

**Mapping**:

| JSON | DB column | Note |
|------|-----------|------|
| `"id"` (stringa) | ❌ NON usato come PK | Serve solo come **chiave di join** con `showings.json`. È il titolo normalizzato dello scraper (`title_normalized`) e **conserva le cifre finali**: «Amori e incantesimi 2» ha id «Amori e incantesimi 2», che è un altro film rispetto a «Amori e incantesimi». |
| `title` | `title` | |
| `title_normalized` | `title_normalized` | ⚠️ **rinormalizzare nel backend** — la normalizzazione dello scraper può differire (em-dash). Meglio NON fidarsi del campo del JSON e ricalcolare via `normalize_title()`, che fonde anche **`&` → `e`** (UCI `AMORI & INCANTESIMI 2` = The Space `Amori e incantesimi 2`). |
| `original_title` | `original_title` | nullable |
| `year` | `year` | int, nullable. ⚠️ In SQL `NULL ≠ NULL`: con `year` NULL la `UNIQUE(title_normalized, year)` **non blocca duplicati a livello DB** — la dedup è garantita dal lookup applicativo in `get_by_natural_key`: un anno NULL è **jolly solo se il candidato è unico** e viene **adottato** (completato) quando incontra l'anno valorizzato. Con più candidati omonimi (remake) non si unisce nulla. |
| `duration` (stringa "X min") | `runtime_minutes` | parsing: estrai int da `"95 min"` → `95` |
| `genres` (array) | `genres` (string CSV) | `",".join(genres)` |
| `director` | `director` | nullable |
| `poster` | `poster_url` | |
| `description` | `synopsis` | |
| `wikidata_id` | `wikidata_id` | UNIQUE, nullable. **Secondo segnale di identità** (dopo la chiave naturale): si scrive solo quando è libero, mai quando è già di un'altra riga — vedi la tabella dei casi sotto |
| — | `id` (DB) | PK autoincrement, generato dal DB |
| — | `created_at` | default `now()` |
| — | `removed_at` | nullable. **Archiviazione** (soft delete), non cancellazione: vedi §4.1 |

**Strategia seed**:

```pseudo
per ogni record film nel JSON:
    title_norm = normalize_title(record["title"])      # NON usare title_normalized del JSON
    year = record.get("year")
    runtime = _parse_duration(record.get("duration"))  # "95 min" → 95 (seed_from_json.py)
    record_norm = {
        "title": record["title"],
        "title_normalized": title_norm,
        "year": year,
        "runtime_minutes": runtime,
        "genres": ",".join(record.get("genres") or []),
        "director": record.get("director"),
        "poster_url": record.get("poster"),
        "synopsis": record.get("description"),
        "original_title": record.get("original_title"),
        "wikidata_id": record.get("wikidata_id"),
    }

    film = film_repo.upsert_from_scraper(db, record_norm)
        # identità a due segnali — un film = una riga (tabella dei casi sotto):
        #   N = SELECT by (title_normalized, year)   [anno jolly incluso]
        #   W = SELECT by wikidata_id                [solo se il payload lo porta;
        #                                             vede anche le righe archiviate]
        #   return film  (con id intera popolata)

    # COSTRUISCI lookup per il prossimo step:
    title_to_id[record["id"]] = film.id    # mappa "titolo stringa JSON" → id intera DB
```

**Tabella dei casi dell'identità** (N = riga per chiave naturale, W = riga che possiede
`wikidata_id` nel DB):

| N | W | Cosa si fa |
|---|---|---|
| riga | stessa riga oppure W = None | upsert di sempre: campi non-null aggiornati + anno NULL adottato |
| None | riga | **riuso**: è lo stesso film tornato con un'altra forma di titolo → si aggiorna quella riga, **mai INSERT** |
| riga | riga **diversa** | **conflitto di identità**: nessun INSERT, nessuna scrittura di `wikidata_id` (non su N, non su W); si aggiornano i soli metadati di N e la coppia finisce in `identity_conflicts` (§4.1) |
| None | None | INSERT (unico caso in cui si inserisce) |

Regole di dettaglio:

- il riuso via `wikidata_id` **non cambia la chiave naturale** (`title_normalized`, `year`) né
  `title`: se una run futura ripropone la forma vecchia senza wikidata, il lookup per chiave deve
  continuare a trovare quella riga — ogni cambio di chiave riapre la porta ai doppioni. La chiave
  è interna: la sua stabilità vale più del titolo corrente;
- il conflitto di identità **non è un errore**: il seed continua, logga `WARNING` e conta.
  Mai `DELETE` nemmeno in conflitto: le due righe restano e la fusione è una decisione umana
  (`python -m app.maintenance.dedup_films --merge A:B`).

⚠️ **Punto critico**: la chiave del dict `title_to_id` è la stringa **originale** del JSON (campo `"id"` non normalizzato), perché è esattamente quella che ritroverò come `film_id` dentro `showings.json`. NON normalizzare la chiave del lookup.

---

## 3. `showings.json` → tabella `showings`

**File**: `scraper/output/showings.json`
**Struttura JSON**:

```json
{
  "generated_at": "2026-06-25T12:56:35...",
  "date_from": "2026-06-25",
  "date_to": "2026-07-02",
  "showings": [
    {
      "film_id": "Ricchi…da morire - Delitti in famiglia",
      "cinema_slug": "postmodernissimo",
      "date": "2026-06-25",
      "times": ["18:30"],
      "source_url": "https://www.postmodernissimo.com/films/ricchi-..."
    },
    ...
  ]
}
```

**Mapping**:

| JSON | DB column | Note |
|------|-----------|------|
| `film_id` (string title) | `film_id` (int) | **lookup obbligatorio**: `title_to_id[record["film_id"]]` (vedi §2). Se non trovato → log + skip record. |
| `cinema_slug` | `cinema_slug` (string FK) | 1:1, identico |
| `date` (ISO string) | `date` (date) | `date.fromisoformat(...)` |
| `times` (array di "HH:MM") | `times` (string JSON) | `json.dumps(times, separators=(",",":"))` |
| `source_url` | `buy_url` | |
| `language` | `language` | nullable; presente per The Space, assente altrove |
| `screen` | `screen` | nullable; conservato solo se proviene da un'unica sala (vedi sotto) |
| — | `scraped_at` | default `now()` |
| — | `removed_at` | nullable. **Archiviazione** (soft delete), non cancellazione: vedi §4.1 |

**Strategia seed — pre-aggregazione obbligatoria**: più sale dello stesso cinema possono
pubblicare lo stesso film con orari diversi, e il JSON contiene **un record per sala**. Poiché
la tabella `showings` ha `UNIQUE(film_id, cinema_slug, date)`, un upsert per record farebbe
vincere l'ultima sala, **perdendo gli orari delle precedenti**. Il seed quindi raggruppa prima
per `(film_db_id, cinema_slug, date)`, unisce tutti gli orari in un'unica riga (dedup + sort) e
fa un solo upsert per gruppo.

```pseudo
aggregated = {}   # chiave: (film_db_id, cinema_slug, date) → record aggregato
per ogni record showing nel JSON:
    film_db_id = title_to_id.get(record["film_id"])
    if film_db_id is None:
        log.warning(f"Film '{record['film_id']}' non trovato nel lookup, skip")
        continue

    key = (film_db_id, record["cinema_slug"], date.fromisoformat(record["date"]))
    agg = aggregated.setdefault(key, {"times": [], "screens": set(), "language": None, "buy_url": None})
    for t in record["times"]:              # unisce gli orari di tutte le sale
        if t and t not in agg["times"]:   # dedup
            agg["times"].append(t)
    if record.get("screen"):               # raccoglie le sale distinte
        agg["screens"].add(record["screen"])
    if not agg["language"] and record.get("language"):
        agg["language"] = record["language"]
    agg["buy_url"] = agg["buy_url"] or record.get("source_url")

per ogni (key, agg) in aggregated:
    showing_repo.upsert(db, {
        "film_id":     key[0],
        "cinema_slug": key[1],
        "date":        key[2],
        "times":       json.dumps(sorted(agg["times"])),
        "language":    agg["language"],
        # screen ambiguo se lo stesso film è in più sale → None
        "screen":      next(iter(agg["screens"])) if len(agg["screens"]) == 1 else None,
        "buy_url":     agg["buy_url"],
    })
    # SELECT by (film_id, cinema_slug, date) → UPDATE times/language/screen/buy_url, oppure INSERT
```

---

## 4. Ordine d'esecuzione del seed

L'ordine è vincolato dalle FK. **Sempre questo ordine**:

```
1. cinemas.json   →  upsert in `cinemas`          (PK slug)
2. films.json     →  upsert in `films`,
                     COSTRUISCI title_to_id        (lookup string → int)
3. showings.json  →  upsert in `showings`,
                     USA title_to_id per film_id intero
4. riconciliazione →  ARCHIVIA i residui (`removed_at`), riattiva ciò che ricompare
```

### 4.1 Riconciliazione: si archivia, mai si cancella

Dopo l'upsert, le righe che non compaiono più nei JSON dell'ultima importazione sono **residui di
run passate** e si **archiviano**: `removed_at = now()`, la riga resta nel DB con tutti i suoi dati e
i suoi showings. Se la riga ricompare nei JSON → `removed_at = NULL` (riattivazione) e i campi si
aggiornano come nell'upsert di sempre. **Mai `DELETE`** (decisione dell'utente, 2026-09-25: «tra 2
anni lo stesso film torna al cinema e voglio riusare/risalire ai dati vecchi»).

| Cosa | Regola |
|---|---|
| **Film** | la chiave naturale `(title_normalized, year)` non è fra quelle importate → archiviato. La regola è l'**assenza**, non la somiglianza: alcuni residui hanno chiavi normalizzate che non assomigliano a nessuna forma attuale dei JSON |
| **Showings** | stessa regola per `(film_id, date)`, ma solo **dentro la finestra** `date_from`/`date_to` di `showings.json` e per i cinema di `cinemas.json`. Fuori finestra non si tocca nulla: è storia |
| **Guardia anti-fonte-rotta** | se per un cinema gli showings importati sono meno di `seed_archive_min_ratio` (default 0.5) di quelli già attivi nel DB nella stessa finestra → l'archiviazione per quel cinema si **salta** e finisce in `skipped_cinemas`: sembra una fonte andata a metà, non una programmazione cambiata |
| **Query pubbliche** | `removed_at IS NULL` su film e showings: un film archiviato non compare, e nemmeno i suoi spettacoli. `removed_at` non è esposto dall'API (è un fatto interno del DB) |
| **Report** | `seed_from_json` ritorna `archived_films`, `reactivated_films`, `archived_showings`, `reactivated_showings`, `skipped_cinemas`, `identity_conflicts`, `duplicate_titles` e `make seed` li stampa: un'archiviazione silenziosa è un'archiviazione che spaventa (stesso principio per i conflitti di identità) |
| **Guardia di identità** | `identity_conflicts` elenca le coppie `(id_N, id_W)` viste durante l'import in cui il payload legava allo stesso `wikidata_id` due righe diverse; `duplicate_titles` le coppie di righe **attive** con lo stesso `title_normalized` ed entrambi `year` NULL (l'unico buco residuo della UNIQUE). Entrambe nel formato `dedup_films --merge A:B`, nessuna fusione automatica |
| **Invariante** | a fine seed la query «coppie con lo stesso `wikidata_id`» deve tornare **0**: il vincolo `UNIQUE(wikidata_id)` la garantisce e la query la certifica nei log invece di darla per scontata |
| **Idempotenza** | rieseguire il seed sugli stessi JSON non cambia nulla: tutti i contatori a 0 |

Le colonne arrivano con una migrazione **idempotente**
(`app/maintenance/migrate_removed_at.py`: `ALTER TABLE` solo se la colonna manca). Il DB contiene
storico e non si ricrea dal seed, quindi qui non serve `create_all` da zero né Alembic. Interruttore:
`seed_archive_enabled` nella config del backend.

---

## 5. Cosa fare se i JSON sono incompleti o malformati

| Scenario | Comportamento |
|----------|---------------|
| File JSON mancante | abort: errore esplicito, exit code != 0 |
| `showings.json` senza `date_from`/`date_to` (o finestra invertita) | abort: errore esplicito (la finestra delimita dove archiviare: senza non si decide nulla) |
| Cinema con slug duplicato dentro lo stesso JSON | log warning, ultima vince |
| Film senza `title` o senza `id` | skip record + log error |
| Showing con `film_id` che non matcha `title_to_id` | skip record + log warning (può capitare se films.json e showings.json sono incoerenti) |
| Showing con `cinema_slug` non in tabella `cinemas` | skip record + log error (segnala disallineamento) |

---

## 6. Esempi pratici (un giro completo)

**Input scraper**:

```json
// films.json
{ "films": [
  { "id": "Dune Parte 2", "title": "Dune — Parte 2", "year": 2024,
    "wikidata_id": "Q97154362", "director": "Denis Villeneuve", "duration": "166 min", ... }
]}

// showings.json
{ "showings": [
  { "film_id": "Dune Parte 2", "cinema_slug": "uci-perugia",
    "date": "2026-06-30", "times": ["18:00", "21:30"], ... }
]}
```

**Stato DB dopo seed**:

```sql
SELECT * FROM films WHERE wikidata_id = 'Q97154362';
-- id=42, title='Dune — Parte 2', title_normalized='dune parte 2',
-- year=2024, director='Denis Villeneuve', runtime_minutes=166, ...

SELECT * FROM showings WHERE film_id = 42 AND date = '2026-06-30';
-- id=789, film_id=42, cinema_slug='uci-perugia', times='["18:00","21:30"]'
```

**Risposta endpoint `GET /api/v1/film/42`** (schema `FilmDetail` — gli `showings` sono `ShowingOut`, piatti; per gli oggetti `cinema`/`film` annidati vedi `GET /showings` in [api.md](api.md)):

```json
{
  "id": 42,
  "title": "Dune — Parte 2",
  "year": 2024,
  "runtime_minutes": 166,
  "director": "Denis Villeneuve",
  "showings": [
    { "id": 789, "date": "2026-06-30", "times": ["18:00", "21:30"], "language": "ITA", "screen": null, "buy_url": null }
  ]
}
```

---

## 7. Verifica del seed

Cosa controllare **dopo** aver lanciato `python -m app.seed_from_json`:

- I tre JSON (`cinemas.json`, `films.json`, `showings.json`) sono presenti in `SCRAPER_OUTPUT_DIR`.
- **Idempotenza**: rieseguire il seed sullo stesso JSON non cambia i conteggi (upsert per identità a due segnali) e la guardia di identità torna vuota (`identity_conflicts` e `duplicate_titles` a `[]`).
- **Guardia di identità**: nel report `identity_conflicts` e `duplicate_titles` sono vuoti (oppure vanno letti e decisi: ogni coppia è pronta per `dedup_films --merge A:B`) e nei log compare «Invariante certificato: 0 coppie con lo stesso `wikidata_id`».
- **Conteggi reali**: li dà `GET /api/v1/admin/dataset-info` (numero di cinema, film e showings, ultima `scraped_at`). Non fissare numeri attesi nel documento: cambiano a ogni run.
- **Nessuno showing orfano**: nei log del seed non compaiono `warning` di film non risolvibili dal lookup (vedi §5).
