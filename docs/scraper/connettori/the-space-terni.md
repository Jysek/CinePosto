# The Space Cinema Terni — scheda connettore

> **Stato**: 🟢 fonte verificata, pronta per il connettore · **Ondata 1** (riuso del
> connettore API di Corciano) · Ricognizione **19 settembre 2026**.
>
> **Come usarla in una sessione nuova** — **nessun prerequisito**: non tocca l'estrattore
> schema.org, è indipendente dalle altre schede. **Allega solo questa scheda.** Riferimento
> gemello: `scraper/scraper/connectors/thespace.py` (Corciano).

## 1. Identità

| Campo | Valore |
|---|---|
| Nome pubblico | **The Space Cinema Terni** (sul sito: "The Space Terni") |
| Slug proposto | `the-space-terni` |
| Comune | Terni (TR) |
| Indirizzo | Viale Donato Bramante, Snc — 05100 Terni TR |
| Coordinate | `42.5727, 12.6355` (dalla mappa embed ufficiale: 42.57265108903491, 12.635527540445901) |
| Sito | `https://www.thespacecinema.it` |
| Pagina cinema | `https://www.thespacecinema.it/cinema/terni/al-cinema` |
| **Venue ID** | **`1006`** (Corciano = `1027`) |

Blocco per `CINEMA_LOCATIONS`:

```python
"the-space-terni": {
    "name": "The Space Cinema Terni",
    # Verificato dal sito ufficiale thespacecinema.it (2026-09-19)
    "address": "Viale Donato Bramante, Snc, 05100 Terni TR",
    "city": "Terni",
    "region": "Umbria",
    "lat": 42.5727,
    "lon": 12.6355,
    "website": "https://www.thespacecinema.it",
},
```

## 2. Etica / robots.txt

`https://www.thespacecinema.it/robots.txt`:

```
User-agent: *
Sitemap: https://www.thespacecinema.it/sitemap.xml
Disallow: /cdn-cgi/
Disallow: /prenotare-il-biglietto/
Disallow: /ordine/
Disallow: /404
Disallow: /il-mio-account
Disallow: /login/reimposta-password
…
```

Gli `Disallow` coprono aree di **account e acquisto biglietti**: noi usiamo solo
`/api/microservice/showings/...`, che è pubblico. Nessuna violazione.

## 3. Studio della tecnica

Il sito è Next.js (Pages Router) con un backend **microservice** dietro `/api/microservice/`.
La programmazione arriva via REST JSON, **la stessa API già usata per Corciano**. Quindi Terni
non è un nuovo scraper: è **lo stesso connettore con un altro `venue id`**.

### 3.1 Flusso di autenticazione (importante)

L'API risponde **401** senza sessione. Il flusso anonimo è:

1. `POST https://www.thespacecinema.it/api/microservice/auth/token` con body `{}` e
   `Accept: application/json`.
   - Risposta: `{"result":{"accessToken":null,…},"responseCode":0}` — **il body è irrilevante**;
   - ciò che conta è il **`Set-Cookie`** di sessione (`accessToken` httpOnly +
     `accessTokenExpirationTime`, ~12h; refresh 7 giorni).
2. Con lo **stesso cookie jar** (`requests.Session`), tutte le chiamate successive rispondono 200.

Verificato il 19/09/2026 con `curl`: senza cookie jar → `401`; dopo il POST auth nella stessa
sessione → `200`. Il connettore esistente usa `requests.Session` e quindi funziona già.

> Il browser aggiunge anche un header `ApiKey` iniettato a build-time (`MICROSERVICE_API_KEY`,
> non presente nel bundle client). **Non serve**: il flusso cookie anonimo basta. Non tentare
> di estrarre quella chiave.

### 3.2 Endpoint utili (verificati)

| Endpoint | Scopo |
|---|---|
| `POST /api/microservice/auth/token` | apre la sessione anonima (cookie) |
| `GET /api/microservice/showings/cinemas` | elenco cinema raggruppati per lettera → **risolve il venue id dal nome** |
| `GET /api/microservice/showings/cinemas/{id}/films?showingDate=YYYY-MM-DD&includesSession=true&includeSessionAttributes=true` | film + sessioni di un giorno |
| `GET /api/microservice/showings/showingDates?cinemaId={id}&minEmbargoLevel=2&forNextWeek=true` | le date con spettacoli |

Verifica del venue id dal payload di `/showings/cinemas` (19/09/2026):

```json
{ "cinemaId": "1006", "cinemaName": "Terni",
  "whatsOnUrl": "https://www.thespacecinema.it/cinema/terni/al-cinema" }
```

### 3.3 Struttura della risposta `/films`

Ogni elemento è un film con `showingGroups` (un gruppo per data) → `sessions`. Campi rilevanti
per il parser (già gestiti in `thespace.py::_parse_api_film` / `_parse_api_showing_groups`):

- `filmTitle`, `filmUrl` (→ `https://www.thespacecinema.it/film/<slug>`);
- `posterImageSrc`, `synopsisShort`, `runningTime`, `isDurationUnknown`, `director`, `genres`;
- `showingGroups[].date`, `showingGroups[].sessions[].startTime` (ISO), `.screenName`,
  `.attributes[]` con `attributeType` ∈ `Language` | `Movie` | `Session`.

Esempio reale di sessione (Terni, 19/09):

```json
{ "startTime": "2026-09-19T17:30:00",
  "screenName": "Sala 2",
  "attributes": [
    { "name": "ITALIANO", "attributeType": "Language" },
    { "name": "2D", "attributeType": "Session" },
    { "name": "BACK ON THE BIG SCREEN", "attributeType": "Movie" }
  ] }
```

## 4. Specifica di implementazione

### 4.1 Refactor di `thespace.py` (preferibile)

Il connettore attuale ha costanti globali (`THE_SPACE_CINEMA_ID = 1027`, nome, slug, URL). Va
**parametrizzato** senza rompere Corciano:

```python
class TheSpaceConnector(BaseConnector):
    def __init__(self, cinema_id: int, name: str, slug: str, cinema_url: str) -> None:
        self._cinema_id = cinema_id
        self._name = name
        self._slug = slug
        self._cinema_url = cinema_url
    ...
```

`cinema_name` / `cinema_slug` ritornano i valori dell'istanza. `_scrape_via_api` costruisce
`…/showings/cinemas/{self._cinema_id}/films?...`. Il fallback browser resta valido (usa
`self._cinema_url`).

In `main.py`:

```python
TheSpaceConnector(1027, THE_SPACE_CINEMA_NAME, THE_SPACE_CINEMA_SLUG, THE_SPACE_CINEMA_URL),
TheSpaceConnector(1006, THE_SPACE_TERNI_NAME, THE_SPACE_TERNI_SLUG, THE_SPACE_TERNI_URL),
```

### 4.2 Risoluzione dinamica del venue id (raccomandato)

Per non dipendere da un id cablato, in `scrape()` si può leggere
`/api/microservice/showings/cinemas` e cercare `cinemaName == "Terni"` (fallback `1006` se la
chiamata fallisce). Il metodo `cinema_name` resta la chiave di ricerca. Questo copre il
"da confermare venue" della ricognizione ed è la stessa robustezza che serve se The Space
rinumera i cinema.

### 4.3 Costanti in `config.py`

```python
THE_SPACE_TERNI_ID = 1006  # venue ID da /api/microservice/showings/cinemas (2026-09-19)
THE_SPACE_TERNI_NAME = "The Space Cinema Terni"
THE_SPACE_TERNI_SLUG = "the-space-terni"
THE_SPACE_TERNI_URL = f"{THE_SPACE_BASE_URL}/cinema/terni/al-cinema"
```

(Le costanti `THE_SPACE_*` di Corciano restano; quelle comuni — base URL, API base, auth URL —
sono già condivise.)

## 5. Insidie note

- **Cookie di sessione**: se il connettore crea una `Session` nuova per ogni data, il POST auth
  va rifatto. Il codice attuale fa un solo `session` per tutto `_scrape_via_api`: **corretto,
  non cambiarlo**.
- **`showingDate`**: sia `YYYY-MM-DD` sia `YYYY-MM-DDT00:00:00` funzionano (verificato). Il sito
  usa la seconda; il connettore usa la prima. Entrambe ok.
- **Fuso orario**: `startTime` è ISO locale senza offset; `showTimeWithTimeZone` ha `+02:00`.
  Il parser attuale usa `startTime` e ne trae `HH:MM`: va bene.
- **Sala**: `screenName` → `Showing.screen`. Utile in UI (multi-sala, 9 sale a Terni).
- **`genres` vuoto** per molti film: nessun problema, completa Wikidata.
- **Fallback browser**: `_scrape_via_browser` è tarato su Corciano; per Terni cambia solo
  l'URL. Verificare che i selettori CSS (`.showing-listing__list > li`, …) valgano anche per
  Terni — se non si è sicuri, lasciare il fallback ma loggare l'errore.

## 6. Test

`scraper/tests/test_thespace.py` già copre il parsing. Aggiungere:

- `test_connector_uses_configured_cinema_id_in_films_url` (istanza Terni → URL contiene `1006`);
- `test_cinema_name_and_slug_come_from_instance` (Corciano e Terni non si confondono);
- `test_resolves_venue_id_from_cinemas_endpoint_by_name` (se si implementa 4.2);
- `test_falls_back_to_hardcoded_venue_id_when_cinemas_endpoint_fails`.

Con una risposta API registrata per Terni:
`tests/fixtures/thespace_terni_films_2026-09-19.json`.

## 7. Aggiornamento `copertura.md`

Nello stesso commit: riga 8, 🟢 → ✅; il campo "Fonte / tecnica" da "**stessa API di Corciano**
(da confermare venue)" a "API REST microservice (venue 1006)"; contatori aggiornati.
