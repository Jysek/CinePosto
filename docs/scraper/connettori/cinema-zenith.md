# Cinema Zenith — scheda connettore

> Verificato su `857c68b` (`2026-09-24`): costanti, connettore e test confrontati col codice;
> il markup del sito osservato il 19/09/2026 non è stato ri-verificato.

> **Stato**: 🟢 fonte verificata, pronta per il connettore · **Ondata 0** (pilota della famiglia
> schema.org) · Ricognizione **19 settembre 2026**.
>
> **Come usarla in una sessione nuova** — è l'**ondata 0**, nessun prerequisito. **Allega
> anche [`README.md`](README.md)**: questa scheda fa nascere l'estrattore condiviso
> `SchemaOrgExtractor`, e il README ne fissa il contratto. Implementa l'estrattore con **tutte
> e tre** le forme (JSON-LD, microdata `content=`, microdata `<time datetime>`) con test per
> ciascuna, così le ondate 1 diventano semplici adattatori: i markup reali delle altre due
> forme sono nelle schede [`cinema-teatro-concordia.md`](cinema-teatro-concordia.md) e
> [`cinema-metropolis.md`](cinema-metropolis.md).

## 1. Identità

| Campo | Valore |
|---|---|
| Nome pubblico | **Cinema Zenith** |
| Slug proposto | `cinema-zenith` |
| Comune | Perugia (PG) |
| Indirizzo | Via Benedetto Bonfigli, 5 — 06126 Perugia PG |
| Coordinate | `43.10421, 12.39403` (OSM `amenity=cinema`, nome "Zenith") |
| Sito | `https://cinemazenith.it` — **senza `www`** (il `www` non risponde) |
| Telefono / prezzi | nel microdata `MovieTheater` (non necessari allo scraper) |

Blocco per `CINEMA_LOCATIONS` in `scraper/scraper/config.py`:

```python
"cinema-zenith": {
    "name": "Cinema Zenith",
    # Verificato dal JSON-LD del sito ufficiale (2026-09-19)
    "address": "Via Benedetto Bonfigli, 5, 06126 Perugia PG",
    "city": "Perugia",
    "region": "Umbria",
    "lat": 43.10421,
    "lon": 12.39403,
    "website": "https://cinemazenith.it",
},
```

## 2. Etica / robots.txt

`https://cinemazenith.it/robots.txt` (blocco Yoast):

```
User-agent: *
Disallow:

Sitemap: https://cinemazenith.it/sitemap_index.xml
```

`Disallow:` vuoto → **tutto consentito**. Nessun rate limit dichiarato: una run al giorno
(03:00) è più che rispettoso. Nessuna autenticazione, nessun cookie necessario.

## 3. Studio del sito

- **Piattaforma**: WordPress. Tema **`zen25`**, plugin **`silver-screen-by-ummon`**
  (Silver Screen by Ummon) che genera i dati strutturati.
- **Custom post type** `film`, URL dettaglio `https://cinemazenith.it/film/<slug>/`
  (singolare `film`, non `films`).
- **Sitemap**: `sitemap_index.xml` → `page-sitemap.xml`, `film-sitemap.xml` (≈102 film
  storici), `event-sitemap.xml`, `exhibition-sitemap.xml`.
- **Pagine utili**:
  - `https://cinemazenith.it/` — homepage, contiene la programmazione della settimana;
  - `https://cinemazenith.it/programmazione-settimana/` — stessa settimana in formato tabella;
  - `https://cinemazenith.it/film/<slug>/` — dettaglio film (metadati + orari).

### Fonte primaria: JSON-LD nella homepage (1 sola richiesta)

La homepage contiene nel `<head>` uno `<script type="application/ld+json">` con un
`@graph` che elenca **tutti i `Movie` della settimana** e **tutti gli `ScreeningEvent`**.
Verificato il 19/09/2026: 4 film, 21 proiezioni, giorni **19→25 settembre** (manca il 24,
nessuno spettacolo). Copre quindi l'intera finestra `get_week_dates()` tranne i giorni vuoti.

Esempio reale (estratto):

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Movie",
      "@id": "https://cinemazenith.it/film/dove-la-fiesta/",
      "name": "Dov’è la Fiesta?",
      "image": "https://cinemazenith.it/wp-content/uploads/2026/09/DLEF_1080X1920-3piccolo.jpg",
      "director": { "@type": "Person", "name": "Niccolò Gentili" },
      "duration": "PT102M"
    },
    {
      "@type": "ScreeningEvent",
      "name": "Dov’è la Fiesta?",
      "workPresented": { "@type": "Movie", "@id": "https://cinemazenith.it/film/dove-la-fiesta/" },
      "startDate": "2026-09-19T18:30:00+02:00",
      "location": { "@type": "MovieTheater", "name": "Cinema Zenith", "address": { "...": "..." } },
      "offers": [{ "@type": "Offer", "price": "3.50", "url": "https://cinemazenith.it/tickets/?show=1517" }]
    }
  ]
}
```

**Campi presenti nel JSON-LD**: `Movie.@id|name|image|director.name|duration`;
`ScreeningEvent.workPresented.@id|startDate|location|offers`.
**Assenti**: `genre`, `description`, `dateCreated` (anno). → completare dalla pagina di
dettaglio o lasciar fare a Wikidata (`metadata.py`, già a valle).

### Fonte secondaria (fallback): `programmazione-settimana`

`https://cinemazenith.it/programmazione-settimana/` espone gli stessi 21 spettacoli ma in
**microdata** con il markup del tema `zen25`:

```html
<div class="sfe_cel sfe_show" itemscope itemtype="http://schema.org/ScreeningEvent">
  <meta itemprop="workPresented" content="Dov’è la Fiesta?">
  <a class="sfe_tktlink" href="https://cinemazenith.it/tickets/?show=1517">
    <time datetime="2026-09-19T18:30:00+02:00" itemprop="startDate">18:30</time>
  </a>
  <div itemprop="location" itemscope itemtype="http://schema.org/MovieTheater">…</div>
  <div itemprop="offers" itemscope itemtype="http://schema.org/AggregateOffer">…</div>
</div>
```

Nota: qui il titolo è in `workPresented` (attributo `content`), **non** in un `Movie` annidato.
L'estrattore deve saper leggere anche questa variante (vedi README, passo 4).

### Dettaglio film: metadati umani

`https://cinemazenith.it/film/dove-la-fiesta/` ha una tabella
`<div class="dt_row"><header class="dt_cel"><strong>Genere:</strong></header>
<div class="dt_cel">Commedia</div></div>` con: **Genere, Regia, Durata, Anno, Nazione,
Titolo originale**, e la sinossi in `.opus-content p`. Utile per arricchire i film, ma
**non necessario per l'MVP**: `fetch_film_detail` può partire come `return None`
(come fa UCI) e aggiungere i campi in una seconda iterazione.

## 4. Specifica di implementazione

**File**: `scraper/scraper/connectors/cinema_zenith.py`
**Classe**: `CinemaZenithConnector(BaseConnector)`

1. `cinema_name` → `CINEMA_ZENITH_NAME`; `cinema_slug` → `"cinema-zenith"`.
2. `scrape(today, dates)`:
   - `GET https://cinemazenith.it/` con `retry_request`;
   - `films = extract_screening_events(resp.text, base_url)` (estrattore condiviso);
   - se `films` è vuoto → ritenta su `https://cinemazenith.it/programmazione-settimana/`
     (fallback, stessa estrazione);
   - errore di rete/parsing → `ScrapeResult(errors=[make_error(...)])`, mai eccezione.
3. Filtro date: tenere solo gli `startDate` in `dates` (default `get_week_dates()`).
4. `fetch_film_detail(url)` → opzionale, `None` per l'MVP.

**Costanti in `config.py`**:

```python
CINEMA_ZENITH_NAME = "Cinema Zenith"
CINEMA_ZENITH_SLUG = "cinema-zenith"
CINEMA_ZENITH_BASE_URL = "https://cinemazenith.it"
CINEMA_ZENITH_URL = f"{CINEMA_ZENITH_BASE_URL}/"
CINEMA_ZENITH_WEEK_URL = f"{CINEMA_ZENITH_BASE_URL}/programmazione-settimana/"
```

**Registrazione** in `scraper/scraper/main.py`: import + `CinemaZenithConnector()` nella lista
`connectors`.

## 5. Insidie note

- **Entità HTML nei titoli**: Castello emette `Paw Patrol &#8211; …`; Zenith usa apostrofi
  tipografici `’`. Sempre `html.unescape` + `normalize_title`.
- **`duration` ISO 8601** (`PT102M`): non è `"102 min"`. `normalize_duration` lo converte
  comunque (`PT102M` → fallback numerico → `"102 min"`; `PT1H49M` → `"109 min"` via
  `_HOURS_MIN_RE`), ma il prefisso `PT` non è riconosciuto esplicitamente. Meglio convertire
  nell'estrattore (`PT102M` → `102 min`) o aggiungere un ramo `PT#M`/`PT#H#M` a
  `normalize_duration`. → **Azione**: test `normalize_duration("PT102M") == "102 min"`.
- **Settimana corta**: il sito pubblica ~6 giorni, non 8. Non è un errore: restituire solo
  le date disponibili.
- **Poster** con URL assoluto: nessun wrapper `/_next/image`, non serve `_clean_poster`.
- La homepage può passare da cache: se un titolo manca, il fallback
  `programmazione-settimana` è la seconda fonte. (Non c'è una pagina di dettaglio per il
  singolo giorno.)

## 6. Test

`scraper/tests/test_cinema_zenith.py`, fixture `tests/fixtures/zenith_home.html` (homepage
registrata) + `zenith_week.html` (fallback).

Casi (nomi comportamentali):

- `test_extracts_movie_and_screening_events_from_jsonld_graph`
- `test_maps_work_presented_id_to_movie_metadata`
- `test_decodes_html_entities_in_title`
- `test_parses_iso_duration_to_minutes`
- `test_filters_events_outside_requested_dates`
- `test_falls_back_to_week_page_when_homepage_has_no_events`
- `test_returns_error_result_when_both_sources_fail`
- `test_returns_empty_list_when_page_has_no_screening_events`

## 7. Aggiornamento `copertura.md`

Nello stesso commit: riga 4, stato 🟢 → ✅; aggiornare il contatore "Sale implementate"
(3 → 4) e la riga "pronte per il connettore" (5 → 4).
