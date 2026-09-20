# Nuovo Cinema Castello — scheda connettore

> **Stato**: 🟢 fonte verificata, pronta per il connettore · **Ondata 1** (famiglia schema.org,
> gemello di Zenith) · Ricognizione **19 settembre 2026**.
>
> **Come usarla in una sessione nuova** — **prerequisito: ondata 0 mergiata**
> (`scraper/scraper/connectors/schema_org.py` deve esistere). **Allega solo questa scheda**:
> l'estrattore condiviso si legge dal repo, non serve il README. Il caso gemello è
> [`cinema-zenith.md`](cinema-zenith.md).

## 1. Identità

| Campo | Valore |
|---|---|
| Nome pubblico | **Nuovo Cinema Castello** |
| Slug proposto | `nuovo-cinema-castello` |
| Comune | Città di Castello (PG) |
| Indirizzo | Piazza Gioberti — 06012 Città di Castello PG |
| Coordinate | `43.45808, 12.24147` (OSM, "Nuovo Cinema Castello") |
| Sito | `https://www.nuovocinemacastello.it` — **`www` obbligatorio**: l'host senza `www` risponde `301` (proxy Aruba) |

Blocco per `CINEMA_LOCATIONS`:

```python
"nuovo-cinema-castello": {
    "name": "Nuovo Cinema Castello",
    # Verificato dal JSON-LD del sito ufficiale (2026-09-19)
    "address": "Piazza Gioberti, 06012 Città di Castello PG",
    "city": "Città di Castello",
    "region": "Umbria",
    "lat": 43.45808,
    "lon": 12.24147,
    "website": "https://www.nuovocinemacastello.it",
},
```

## 2. Etica / robots.txt

`https://www.nuovocinemacastello.it/robots.txt`:

```
User-agent: *
Disallow: /wp-admin/
Allow: /wp-admin/admin-ajax.php

Sitemap: https://www.nuovocinemacastello.it/wp-sitemap.xml
```

Solo `/wp-admin/` è escluso: la programmazione è pubblica. Nessun cookie/login.

## 3. Studio del sito

- **Piattaforma**: WordPress, tema **`zen25`** — *lo stesso tema di Cinema Zenith*. Plugin
  rilevati: `mailpoet` (newsletter); i dati strutturati sono generati dal tema/stack Ummon
  (`Silver Screen`). Firma: `sitemap_index` non Yoast ma **`wp-sitemap.xml`** nativo.
- **Custom post type**: `venue`, `screen`, `film`, `event` (visibili come
  `wp-sitemap-posts-<tipo>-1.xml`).
- **URL dettaglio film**: `https://www.nuovocinemacastello.it/film/<slug>/` (singolare).
- **Sitemap film**: `https://www.nuovocinemacastello.it/wp-sitemap-posts-film-1.xml` (≈91 film
  storici).
- **Homepage**: `https://www.nuovocinemacastello.it/`.

### Fonte primaria: JSON-LD nella homepage (1 sola richiesta)

Identica a Zenith: `<script type="application/ld+json">` con `@graph` di `Movie` +
`ScreeningEvent`. Verificato il 19/09/2026: **5 film, 24 proiezioni, giorni 19→23 settembre**.

Esempio reale (l'unica differenza rispetto a Zenith è che i titoli arrivano con entità HTML):

```json
{
  "@type": "Movie",
  "@id": "https://www.nuovocinemacastello.it/film/paw-patrol-missione-dinosauri/",
  "name": "Paw Patrol &#8211; Missione Dinosauri",
  "image": "https://www.nuovocinemacastello.it/wp-content/uploads/2026/09/Paw-locandinapg1.jpg",
  "director": { "@type": "Person", "name": "Cal Brunker" },
  "duration": "PT82M"
}
```

```json
{
  "@type": "ScreeningEvent",
  "name": "Paw Patrol &#8211; Missione Dinosauri",
  "workPresented": { "@type": "Movie", "@id": "https://www.nuovocinemacastello.it/film/paw-patrol-missione-dinosauri/" },
  "startDate": "2026-09-19T17:15:00+02:00",
  "location": { "@type": "MovieTheater", "name": "Nuovo Cinema Castello", "address": { "...": "..." } },
  "offers": [{ "@type": "Offer", "name": "Prezzo unico", "price": "7.00" }]
}
```

Stessi campi assenti di Zenith: `genre`, `description`, `dateCreated`.

### Fonte secondaria: pagina dettaglio (microdata `zen25`)

`https://www.nuovocinemacastello.it/film/serpenti/` contiene microdata del tema `zen25`:
`Movie` + `ScreeningEvent` con `<time datetime="…" itemprop="startDate">` (verificato: 6
proiezioni). La stessa pagina espone la tabella `dt_row` con **Genere** (`Drammatico, commedia`),
**Regia**, **Durata**, **Anno**, **Nazione**, **Titolo originale** e la sinossi.

> Non c'è una pagina settimanale equivalente a `programmazione-settimana` di Zenith; il
> fallback per Castello è il **dettaglio film** (una richiesta per film) oppure accettare
> la sola homepage.

## 4. Specifica di implementazione

Poiché Zenith e Castello condividono tema e markup, **non duplicare il parser**: implementare
prima Zenith (ondata 0) e riusare `SchemaOrgExtractor`. Castello diventa un adattatore di ~40
righe.

**File**: `scraper/scraper/connectors/nuovo_cinema_castello.py`
**Classe**: `NuovoCinemaCastelloConnector(BaseConnector)`

1. `cinema_slug` → `"nuovo-cinema-castello"`.
2. `scrape(today, dates)`:
   - `GET https://www.nuovocinemacastello.it/` con `retry_request`;
   - `films = extract_screening_events(resp.text, base_url)`;
   - fallback (opzionale, ondata 1.1): per ogni `Movie.@id` senza spettacoli nella finestra,
     `GET` il dettaglio e ri-estrai;
   - errori → `ScrapeResult(errors=[…])`.
3. `fetch_film_detail(url)` → opzionale: parse `dt_row` per genere/anno (o `None`).

**Costanti in `config.py`**:

```python
NUOVO_CASTELLO_NAME = "Nuovo Cinema Castello"
NUOVO_CASTELLO_SLUG = "nuovo-cinema-castello"
NUOVO_CASTELLO_BASE_URL = "https://www.nuovocinemacastello.it"
NUOVO_CASTELLO_URL = f"{NUOVO_CASTELLO_BASE_URL}/"
```

**Registrazione** in `main.py` accanto a `CinemaZenithConnector()`.

## 5. Insidie note

- **`www` obbligatorio**: senza `www` si ottiene un `301` verso il proxy Aruba; usare sempre
  `https://www.nuovocinemacastello.it`.
- **Entità HTML nei titoli** (`&#8211;`, `&egrave;`): `html.unescape` prima di `normalize_title`.
- **Titolo duplicato**: `ScreeningEvent.name` e `Movie.name` portano lo stesso titolo; usare
  `Movie.name` (via `workPresented.@id`) come sorgente unica.
- **Durata ISO** `PT82M`: vedi nota in [cinema-zenith.md](cinema-zenith.md) §5.
- Settimana pubblicata ~5 giorni (19→23), non 8.

## 6. Test

`scraper/tests/test_nuovo_cinema_castello.py`, fixture `tests/fixtures/castello_home.html`.

- `test_extracts_five_movies_from_jsonld_graph`
- `test_decodes_numeric_html_entities_in_title`
- `test_maps_screening_to_movie_via_work_presented_id`
- `test_filters_events_outside_requested_dates`
- `test_returns_error_result_when_homepage_unreachable`

I test dell'estrattore condiviso coprono già JSON-LD/entità/durate: qui restano i casi
specifici del sito.

## 7. Aggiornamento `copertura.md`

Nello stesso commit: riga 5, 🟢 → ✅; contatori "Sale implementate" e "pronte" aggiornati.
