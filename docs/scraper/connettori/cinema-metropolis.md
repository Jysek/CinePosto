# Cinema Metropolis — scheda connettore

> **Stato**: 🟢 fonte verificata, pronta per il connettore · **Ondata 1** (famiglia schema.org,
> variante **microdata su pagina di dettaglio**) · Ricognizione **19 settembre 2026**.
>
> **Come usarla in una sessione nuova** — **prerequisito: ondata 0 mergiata**
> (`schema_org.py` deve esistere). **Allega solo questa scheda.** Il ramo microdata
> `content=` viene introdotto da [`cinema-teatro-concordia.md`](cinema-teatro-concordia.md):
> se quella sessione non è ancora passata, aggiungilo qui.

## 1. Identità

| Campo | Valore |
|---|---|
| Nome pubblico | **Cinema Metropolis** (nel microdata: "Metropolis Cinema Umbertide") |
| Slug proposto | `cinema-metropolis` |
| Comune | Umbertide (PG) |
| Indirizzo | Piazza Carlo Marx — 06019 Umbertide PG (dal microdata `MovieTheater`) |
| Coordinate | `43.30572, 12.33572` (OSM, "Metropolis cinema") |
| Telefono | `075 997 5324` (microdata, non serve) |
| Sito | `https://www.cinemametropolis.it` — `www` obbligatorio |

Blocco per `CINEMA_LOCATIONS`:

```python
"cinema-metropolis": {
    "name": "Cinema Metropolis",
    # Verificato dal microdata del sito ufficiale (2026-09-19)
    "address": "Piazza Carlo Marx, 06019 Umbertide PG",
    "city": "Umbertide",
    "region": "Umbria",
    "lat": 43.30572,
    "lon": 12.33572,
    "website": "https://www.cinemametropolis.it",
},
```

## 2. Etica / robots.txt

`https://www.cinemametropolis.it/robots.txt` (blocco Yoast):

```
User-agent: *
Disallow:

Sitemap: https://www.cinemametropolis.it/sitemap_index.xml
```

`Disallow:` vuoto → tutto consentito.

## 3. Studio del sito

- **Piattaforma**: WordPress, tema **`postmetro`** (stack Ummon), `sitemap_index.xml` Yoast,
  plugin vari (`contact-form-7`, `google-site-kit`, …).
- **URL dettaglio film**: `https://www.cinemametropolis.it/films/<slug>/` (**plurale**).
- **Sitemap film**: `https://www.cinemametropolis.it/films-sitemap.xml` (≈500 film storici).
- **Pagine utili**:
  - `/` homepage — carosello dei film **in programmazione** (microdata `Movie`, **senza orari**);
  - `/oggi-in-sala/` — **solo oggi** (microdata `ScreeningEvent`, verificato 3 proiezioni il 19/09);
  - `/films/<slug>/` — dettaglio film, **con la settimana completa** di spettacoli.

### Il punto delicato: la homepage NON ha gli orari

Verificato il 19/09/2026:

| Pagina | `Movie` | `ScreeningEvent` | Copertura |
|---|---|---|---|
| `/` (homepage) | 11 (≈6 film unici + duplicati slider) | **0** | solo titoli/poster, nessun orario |
| `/oggi-in-sala/` | 5 | 3 | solo la data odierna |
| `/films/serpenti/` | 9 | 8 | **giorni 14→23 settembre** |

→ La fonte della settimana è la **pagina di dettaglio film**. La homepage serve solo a
scoprire *quali* film sono in programmazione adesso.

### Markup reale — dettaglio film (`/films/serpenti/`)

```html
<div class="film-orari"> 17 - 23 settembre </div>
<table class="w100"><tbody class="table_showtimes">
  <tr class="tablerow">
    <td class="cell_day"><span class="tabdaynor">sabato 19</span>…</td>
    <td class="cell_time">
      <ul class="list_showtimes">
        <li itemscope itemtype="http://schema.org/ScreeningEvent">
          <meta itemprop="name" content="Serpenti">
          <div itemprop="location" itemscope itemtype="http://schema.org/MovieTheater">
            <meta itemprop="name" content="Metropolis Cinema Umbertide">
            <meta itemprop="address" content="Piazza Carlo Marx - 06019 Umbertide (PG)">
          </div>
          <div itemprop="workPresented" itemscope itemtype="http://schema.org/Movie">
            <meta itemprop="name" content="Serpenti">
            <meta itemprop="image" content="…/serpenti-1.jpg">
            <meta itemprop="url" content="https://www.cinemametropolis.it/films/serpenti/">
            <meta itemprop="description" content="Paolo Marra ha ucciso sua moglie…">
            <meta itemprop="duration" content="PT88M">
            <meta itemprop="director" content="Roberto De Paolis">
            <meta itemprop="dateCreated" content="2026">
          </div>
          <meta itemprop="url" content="https://www.cinemametropolis.it/films/serpenti/">
          <meta itemprop="duration" content="PT88M">
          <meta itemprop="description" content="…">
          <meta itemprop="image" content="…/serpenti-1.jpg">
          <meta itemprop="performer" content="Leonardo Lidi, Alessandro Borghi, …">
          <div itemprop="startDate" content="2026-09-19T18:30:00+02:00" class="timeslot">18:30</div>
          <meta itemprop="endDate" content="2026-09-19T19:58:00+02:00">
        </li>
        …
      </ul>
    </td>
  </tr>
</tbody></table>
```

Stesso pattern di Concordia: `startDate` in `content=`. Metadati completi
(`description`, `duration`, `director`, `dateCreated`, `performer`) sono già qui: **non serve
un secondo fetch di dettaglio**.

Nota di colore: la pagina **non** ha un `<dl>` come Concordia; genere/anno umani stanno in una
riga di testo (`Titolo originale id. Drammatico, durata 88 min, colore - Italia, 2026`). Il
genere, se serve, va preso da lì (regex) o lasciato a Wikidata.

### Scoperta dei film in programmazione

Homepage: i `Movie` sono in card con `meta[itemprop=url]` verso `/films/<slug>/`.
Verificato: 6 link unici (Serpenti, Paw Patrol – Missione Dinosauri, Naza, Digger,
Palestina 36, Wild Horse Nine). Sono i film **correnti**.

## 4. Specifica di implementazione

**File**: `scraper/scraper/connectors/cinema_metropolis.py`
**Classe**: `CinemaMetropolisConnector(BaseConnector)`

1. `cinema_slug` → `"cinema-metropolis"`.
2. `scrape(today, dates)` — **due fasi**:
   - **Fase A**: `GET https://www.cinemametropolis.it/`; raccogli gli URL unici dei film
     dai `Movie[itemprop=url]` (o `a[href*="/films/"]`).
   - **Fase B**: per ogni URL, `GET` la pagina e `extract_screening_events(html, url)`;
     accumula i `Film` deduplicando per `title_normalized`.
   - Filtra gli eventi sulle `dates`; se un film non ha spettacoli nella finestra, scartalo.
   - Un errore su **una** pagina film non deve fermare le altre: `errors.append(...)` e
     prosegui (come fa `thespace.py` per-data).
3. `fetch_film_detail(url)` → `None`: i metadati sono già nella pagina di dettaglio.

> Nota di costo: ≈6–10 richieste/run (1 homepage + N film). Accettabile per una run al giorno.
> Se in futuro la lista dei film correnti si allunga, valutare `/oggi-in-sala/` per ridurre
> (ma perde i film che iniziano nei giorni successivi).

**Costanti in `config.py`**:

```python
METROPOLIS_NAME = "Cinema Metropolis"
METROPOLIS_SLUG = "cinema-metropolis"
METROPOLIS_BASE_URL = "https://www.cinemametropolis.it"
METROPOLIS_URL = f"{METROPOLIS_BASE_URL}/"
METROPOLIS_TODAY_URL = f"{METROPOLIS_BASE_URL}/oggi-in-sala/"
```

**Registrazione** in `main.py`.

## 5. Insidie note

- **La homepage non ha orari**: chi implementa partendo dalla homepage senza leggere questa
  scheda non troverà nessuno `ScreeningEvent` (0 nel markup). Il percorso giusto è A+B.
- **Entità HTML** in titoli e descrizioni: `&#8211;`, `&eacute;`, `&rsquo;`. `html.unescape`
  (in `models.film_to_dict` c'è già un `html.unescape`, ma applicarlo anche al match dei titoli).
- **`Movie` ripetuto** (antenato + `workPresented`): dedup per `@id`/`url`.
- **Film storici**: la `films-sitemap.xml` ha ~500 titoli vecchi. **Non** usarla per la
  programmazione: usare solo i film linkati dalla homepage.
- **`itemtype` con apici doppi** qui (Concordia usa singoli): il parser deve gestirli entrambi.

## 6. Test

`scraper/tests/test_cinema_metropolis.py`, fixture
`tests/fixtures/metropolis_home.html` (lista film) e `tests/fixtures/metropolis_film_serpenti.html`.

- `test_collects_current_film_urls_from_homepage`
- `test_ignores_films_sitemap_archive`
- `test_extracts_week_screenings_from_film_detail`
- `test_parses_start_date_from_content_attribute`
- `test_continues_when_one_film_detail_fails`
- `test_filters_events_outside_requested_dates`
- `test_returns_error_result_when_homepage_unreachable`

## 7. Aggiornamento `copertura.md`

Nello stesso commit: riga 6, 🟢 → ✅; contatori aggiornati.
