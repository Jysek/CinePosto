# Cinema Teatro Concordia — scheda connettore

> **Stato**: 🟢 fonte verificata, pronta per il connettore · **Ondata 1** (famiglia schema.org,
> variante **microdata**) · Ricognizione **19 settembre 2026**.
>
> **Come usarla in una sessione nuova** — **prerequisito: ondata 0 mergiata**
> (`schema_org.py` deve esistere). **Allega solo questa scheda.** Se il ramo microdata
> dell'estrattore non c'è ancora, aggiungilo qui (è questa la sessione che lo introduce).

## 1. Identità

| Campo | Valore |
|---|---|
| Nome pubblico | **Cinema Teatro Concordia** (nel microdata: "Cinema Teatro Concordia Marsciano") |
| Slug proposto | `cinema-teatro-concordia` |
| Comune | Marsciano (PG) |
| Indirizzo | Largo Carlo Goldoni 9 — 06055 Marsciano PG (dal microdata `MovieTheater`) |
| Coordinate | `42.90966, 12.33726` (OSM, "Cinema Concordia") |
| Telefono | `+39 075 874 8403` (microdata, non serve allo scraper) |
| Sito | `https://www.cineconcordia.it` — `www` obbligatorio (senza `www` → `301` Aruba) |

Blocco per `CINEMA_LOCATIONS`:

```python
"cinema-teatro-concordia": {
    "name": "Cinema Teatro Concordia",
    # Verificato dal microdata del sito ufficiale (2026-09-19)
    "address": "Largo Carlo Goldoni 9, 06055 Marsciano PG",
    "city": "Marsciano",
    "region": "Umbria",
    "lat": 42.90966,
    "lon": 12.33726,
    "website": "https://www.cineconcordia.it",
},
```

## 2. Etica / robots.txt

`https://www.cineconcordia.it/robots.txt` (blocco Yoast):

```
User-agent: *
Disallow:

Sitemap: https://www.cineconcordia.it/sitemap_index.xml
```

`Disallow:` vuoto → tutto consentito. Nessun login/cookie.

## 3. Studio del sito

- **Piattaforma**: WordPress, tema **`concordia`** (stack Ummon), `sitemap_index.xml` Yoast.
- **Custom post type**: `films` (plurale), `eventi`, `rassegne`.
- **URL dettaglio film**: `https://www.cineconcordia.it/films/<slug>/` (**plurale `films`**).
- **Sitemap film**: `https://www.cineconcordia.it/films-sitemap.xml`.
- **Pagine utili**: homepage `/`, `https://www.cineconcordia.it/in-programmazione/`
  (contiene la stessa settimana).

### Fonte primaria: microdata nella homepage (1 sola richiesta)

La homepage **non** ha JSON-LD con gli spettacoli: la programmazione è in **microdata
schema.org**, annidata in `div[itemscope][itemtype='http://schema.org/ScreeningEvent']`.

Verificato il 19/09/2026: 2 film attivi, **10 proiezioni, giorni 19→23 settembre**.
La struttura giorni è `<div class="day_films" id="day0_films">` … `id="day6_films"`
(day0 = oggi), ma **non serve**: ogni evento porta il `startDate` ISO completo.

Markup reale (apici singoli su `itemtype`, `startDate` in `content=`):

```html
<div class="w_film_cont" itemscope itemtype="http://schema.org/Movie">
  <meta itemprop="name" content="THE INVITE &#8211; IL PIACERE È TUTTO..."/>
  <meta itemprop="image" content="https://www.cineconcordia.it/wp-content/uploads/2026/09/…jpg"/>
  <meta itemprop="url" content="https://www.cineconcordia.it/films/the-invite-il-piacere-e-tutto-nostro/"/>
  <meta itemprop="description" content="Una graffiante commedia sexy, …"/>
  <meta itemprop="duration" content="PT107M"/>
  <meta itemprop="director" content="Olivia Wilde"/>
  <meta itemprop="dateCreated" content="2026"/>

  <div class="w_film_showtimes clearfix">
    <div itemscope itemtype='http://schema.org/ScreeningEvent' class="w_film_showtime_cont">
      <meta itemprop="name" content="THE INVITE &#8211; IL PIACERE È TUTTO..."/>
      <div itemprop="location" itemscope itemtype="http://schema.org/MovieTheater">
        <meta itemprop="name" content="Cinema Teatro Concordia Marsciano"/>
        <meta itemprop="address" content="Largo Carlo Goldoni 9, 06055 Marsciano (PG) - Italy"/>
      </div>
      <div itemprop="workPresented" itemscope itemtype="http://schema.org/Movie">…</div>
      <meta itemprop="url" content="https://www.cineconcordia.it/films/the-invite-il-piacere-e-tutto-nostro/"/>
      <meta itemprop="duration" content="PT107M"/>
      <div itemprop="startDate" content="2026-09-19T18:30:00+02:00" class="w_film_showtime">18:30</div>
      <meta itemprop="endDate" content="2026-09-19T20:17:00+02:00"/>
    </div>
  </div>
</div>
```

**Differenze rispetto a Zenith/Castello**:
- non c'è JSON-LD con gli spettacoli → si parte dal ramo microdata dell'estrattore;
- `startDate` sta in `content=` di un `<div>`, **non** in `<time datetime>`;
- il `Movie` è annidato **dentro** lo `ScreeningEvent` (`workPresented`) **e** ripetuto a
  livello superiore (`w_film_cont`); usare `workPresented` o il `Movie` antenato;
- `endDate` presente (utile come sanity check, non salvato).

### Dettaglio film: metadati umani

`https://www.cineconcordia.it/films/the-invite-il-piacere-e-tutto-nostro/` contiene:

```html
<div class="film_data">
  <dl>
    <dt>Titolo originale</dt><dd style="font-style: italic;">The Invite</dd>
    <dt>Regia</dt><dd>Olivia Wilde</dd>
    <dt>Cast</dt><dd>Seth Rogen, Olivia Wilde, Penélope Cruz, …</dd>
    <dt>Genere</dt><dd>Commedia, Drammatico</dd>
    <dt>Durata</dt><dd>107 - colore</dd>
    <dt>Produzione</dt><dd>USA (2026)</dd>
    <dt>Distribuzione</dt><dd>I WONDER</dd>
  </dl>
</div>
```

Da qui: **Genere** (split su virgola), **Titolo originale**, **Produzione** → anno.

## 4. Specifica di implementazione

**File**: `scraper/scraper/connectors/cinema_teatro_concordia.py`
**Classe**: `CinemaTeatroConcordiaConnector(BaseConnector)`

1. `cinema_slug` → `"cinema-teatro-concordia"`.
2. `scrape(today, dates)`:
   - `GET https://www.cineconcordia.it/`;
   - `films = extract_screening_events(resp.text, base_url)` — l'estrattore deve gestire
     `div[itemprop=startDate][content]`;
   - filtro sulle `dates`;
   - errore → `ScrapeResult(errors=[…])`.
3. `fetch_film_detail(url)` → opzionale: parse `div.film_data dl` per genere/titolo originale.

**Costanti in `config.py`**:

```python
CONCORDIA_NAME = "Cinema Teatro Concordia"
CONCORDIA_SLUG = "cinema-teatro-concordia"
CONCORDIA_BASE_URL = "https://www.cineconcordia.it"
CONCORDIA_URL = f"{CONCORDIA_BASE_URL}/"
```

**Registrazione** in `main.py`.

## 5. Insidie note

- **`itemtype` con apici singoli**: `itemtype='http://schema.org/ScreeningEvent'`. Le regex
  devono accettare `"` e `'`; BeautifulSoup (`soup.select('[itemtype*="ScreeningEvent"]')`)
  è la via sicura.
- **Titoli con entità HTML**: `&#8211;` (en dash), `È`. `html.unescape`.
- **`Movie` duplicato** (antenato + `workPresented`): deduplicare per `@id`/`url`.
- **`Durata` umana** nel dettaglio: `"107 - colore"` → `normalize_duration` estrae `107 min`
  (fallback numerico). Verificare che non diventi `"1 min"`.
- Il selettore `day0_films…day6_films` **non va usato** per il raggruppamento: leggere
  `startDate`. Le classi del tema cambiano.

## 6. Test

`scraper/tests/test_cinema_teatro_concordia.py`, fixture
`tests/fixtures/concordia_home.html`.

- `test_parses_start_date_from_content_attribute`
- `test_reads_screening_event_with_single_quoted_itemtype`
- `test_deduplicates_movie_appearing_both_ancestor_and_work_presented`
- `test_maps_movie_duration_pt_to_minutes`
- `test_filters_events_outside_requested_dates`
- `test_returns_empty_list_when_no_screening_events`
- `test_returns_error_result_when_homepage_unreachable`

## 7. Aggiornamento `copertura.md`

Nello stesso commit: riga 7, 🟢 → ✅; contatori aggiornati.
