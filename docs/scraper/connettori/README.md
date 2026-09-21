# Connettori — schede di implementazione

> Verificato su `0c56a7e` (`2026-09-21`): intestazione aggiunta, contenuto non ancora ricontrollato.

Schede pronte per essere passate a una **sessione nuova**: contengono lo studio fatto sul
sito (piattaforma, markup reale, URL, insidie) e la specifica di implementazione per il
connettore CinePosto.

> Ricognizione siti: **19 settembre 2026**, con User-Agent identificabile del progetto
> `CinePosto/1.0 (+https://github.com/Jysek/CinePosto; 55837328+Jysek@users.noreply.github.com)`.
> I markup citati sono stati letti dal vivo in quella data; se il sito cambia, i test
> fixture vanno ri-registrati.

## Ordine di esecuzione (obbligatorio)

L'estrattore condiviso `SchemaOrgExtractor` **nasce con Zenith** e poi viene riusato: senza
l'ondata 0 fatta, le schede Castello/Concordia/Metropolis non hanno il codice su cui appoggiarsi.

```
ONDATA 0   cinema-zenith.md + README.md   -> crea scraper/connectors/schema_org.py
ONDATA 1   nuovo-cinema-castello.md       -> adattatore JSON-LD (quasi gratis)
           cinema-teatro-concordia.md     -> aggiunge il ramo microdata content=
           cinema-metropolis.md           -> microdata + crawl a 2 fasi
SEMPRE     the-space-terni.md             -> indipendente (refactor thespace.py)
```

| Sessione | Allega | Prerequisito |
|---|---|---|
| **0 — Zenith** | `README.md` **+** `cinema-zenith.md` | nessuno |
| **1a — Castello** | `nuovo-cinema-castello.md` | ondata 0 mergiata |
| **1b — Concordia** | `cinema-teatro-concordia.md` | ondata 0 mergiata |
| **1c — Metropolis** | `cinema-metropolis.md` | ondata 0 mergiata |
| **T — Terni** | `the-space-terni.md` | nessuno |

Regola: se la scheda dice "riusa `SchemaOrgExtractor`", la sessione **legge il file**
`schema_org.py` dal repo e ci si adegua; il README qui sotto è solo il contratto di partenza.

**Prompt pronto da incollare** (adattare la scheda):

> Implementa il connettore descritto in questa scheda seguendo `AGENTS.md`. Rispetta la
> specifica tecnica (fonte, markup, mapping), aggiungi i test indicati con nomi che
> descrivono il comportamento, aggiorna `docs/scraper/copertura.md` nello stesso commit.
> Per creare le fixture recupera le pagine **una volta sola** con lo User-Agent del progetto
> (no scraping live ripetuto). Chiudi con `make lint` e `make test-scraper` verdi.

## Quali sale hanno una scheda qui

Una scheda dedicata serve quando la tecnica **non è banale** o va studiata prima di scrivere il
codice (markup proprietario, microdata, API da ricostruire). Le sale coperte da connettori
diretti — **PostModernissimo, The Space Cinema Corciano, UCI Cinemas Perugia** — sono descritte
in [../architecture.md](../architecture.md). L'elenco completo e aggiornato delle **8 sale
implementate** sta in [../copertura.md](../copertura.md).

## Indice

| Cinema | Scheda | Famiglia tecnica | Fonte primaria |
|---|---|---|---|
| Cinema Zenith | [cinema-zenith.md](cinema-zenith.md) | schema.org JSON-LD (tema `zen25` + Silver Screen by Ummon) | homepage, 1 richiesta |
| Nuovo Cinema Castello | [nuovo-cinema-castello.md](nuovo-cinema-castello.md) | schema.org JSON-LD (tema `zen25`) | homepage, 1 richiesta |
| Cinema Teatro Concordia | [cinema-teatro-concordia.md](cinema-teatro-concordia.md) | schema.org microdata (tema `concordia`) | homepage, 1 richiesta |
| Cinema Metropolis | [cinema-metropolis.md](cinema-metropolis.md) | schema.org microdata (tema `postmetro`) | homepage + N dettagli film |
| The Space Cinema Terni | [the-space-terni.md](the-space-terni.md) | API REST microservice (come Corciano) | API, 1 richiesta/data |

Le prime quattro condividono lo stesso vocabolario di dati ([schema.org](https://schema.org)
`Movie` + `ScreeningEvent`) ma **tre forme diverse**:

1. **JSON-LD `@graph`** nel `<head>` — Zenith, Nuovo Cinema Castello.
2. **Microdata** con `div[itemprop=startDate][content=ISO]` — Concordia, Metropolis (dettaglio).
3. **Microdata** con `<time datetime=ISO itemprop=startDate>` — pagine dettaglio `zen25`.

Regola d'oro della `copertura.md`: **agganciarsi ai microdata/JSON-LD, mai alle classi CSS
del tema** (`pw_row`, `sfe_cel`, `w_film_showtime`, `timeslot`… cambiano da tema a tema).

---

## Estrattore condiviso: `SchemaOrgExtractor`

Obiettivo DRY: **una sola logica di parsing** parametrizzata, e un adattatore per sito che
dice solo *dove* prendere l'HTML. Vive in `scraper/scraper/connectors/schema_org.py`.

### API pubblica (funzioni pure, testabili senza rete)

```python
def extract_screening_events(html: str, base_url: str) -> list[Film]:
    """Estrae Film con present_in da una pagina che contiene Movie+ScreeningEvent
    in JSON-LD e/o microdata. NON filtra per data: restituisce tutto ciò che la
    pagina espone. Non fa I/O: riceve l'HTML già scaricato."""

def filter_films_to_dates(films: list[Film], dates: list[str] | None) -> list[Film]:
    """Tiene solo gli spettacoli nelle date richieste; scarta i Film senza spettacoli
    residui. `dates=None` → nessun filtro. La chiama il connettore, non l'estrattore."""

def extract_jsonld_graph(html: str) -> list[dict]:
    """Ritorna il @graph (o la lista di oggetti) di tutti i <script type=application/ld+json>
    che contengono almeno un ScreeningEvent. Lista vuota se assenti."""

def extract_microdata_items(html: str, type_: str) -> list[Tag]:
    """Tutti gli elementi con itemtype schema.org/<type_>, nesting-aware."""
```

### Algoritmo

1. Prova **JSON-LD** (`extract_jsonld_graph`). Se ci sono `ScreeningEvent` → usa quella via.
2. Altrimenti **microdata** (`extract_microdata_items(html, "ScreeningEvent")`).
3. Per ogni evento ricava `startDate` da **una delle due forme**:
   - `time[itemprop=startDate][datetime]` (tema `zen25`);
   - `[itemprop=startDate][content]` (temi `concordia`/`postmetro`).
4. Risale al film con `workPresented`, che ha **tre forme possibili**:
   - JSON-LD: `workPresented["@id"]` → `Movie["@id"]`;
   - microdata con `Movie` annidato: `[itemprop=workPresented][itemtype$=Movie]` → leggi i
     suoi `itemprop` (`name`, `image`, `url`, `duration`, `director`, `dateCreated`);
   - microdata con `workPresented` **come stringa**: `<meta itemprop="workPresented"
     content="Titolo">` (pagina `programmazione-settimana` di Zenith) → il titolo è il
     `content`; gli altri metadati vanno cercati nel `Movie` antenato o restano `None`.
5. Normalizza `startDate` con `datetime.fromisoformat` → `date` `YYYY-MM-DD`, `time` `HH:MM`.
   Raggruppa gli orari per data (la consolidazione vera avviene poi in
   `models._consolidate_showings`).
6. **Il filtro per data NON sta qui**: il connettore chiama `filter_films_to_dates(films, dates)`
   subito dopo l'estrazione.

### Campi mappati

| schema.org | `Film` / `Showing` | Note |
|---|---|---|
| `Movie.name` | `Film.title` | `html.unescape` obbligatorio (`&#8211;`) |
| `Movie.@id` / `url` | `Showing.source_url` | URL pagina dettaglio |
| `Movie.image` | `Film.source_poster` | URL assoluto |
| `Movie.director.name` (JSON-LD) / `director` (microdata) | `Film.director` | stringa |
| `Movie.duration` `PT102M` | `Film.duration` | l'estrattore converte `PT#H#M`/`PT#M` → `"N min"`; `normalize_duration` resta come rete di sicurezza |
| `Movie.dateCreated` (microdata) | `Film.year` | JSON-LD non lo emette |
| `Movie.genre` | `Film.genres` | **assente** in JSON-LD; da dettaglio o Wikidata |
| `ScreeningEvent.startDate` | `Showing.date` + `Showing.times` | ISO con offset `+02:00` |
| `ScreeningEvent.location.name` | (verifica) | utile solo come sanity check del cinema |

`Film.title_normalized = normalize_title(title)`.

### Registrare le fixture (una volta sola)

Con lo User-Agent del progetto, una richiesta per pagina, poi si salva l'HTML:

```bash
UA="CinePosto/1.0 (+https://github.com/Jysek/CinePosto; 55837328+Jysek@users.noreply.github.com)"
curl -s -A "$UA" "https://cinemazenith.it/" -o scraper/tests/fixtures/zenith_home.html
```

### Test dell'estrattore (senza rete)

Fixtures HTML committate in `scraper/tests/fixtures/`, una per forma di markup:

- `schema_org_jsonld_zenith.html` → atteso: N film, M screening, date attese;
- `schema_org_microdata_concordia.html` → idem con `content=`;
- `schema_org_microdata_zen25_detail.html` → idem con `<time datetime>`;
- casi limite: JSON-LD malformato → fallback microdata; pagina senza eventi → `[]`;
  entità HTML nel titolo; evento senza `startDate` → scartato.

I connettori per cinema sono **sottili**: scaricano l'HTML e delegano all'estrattore.
Questo è il punto in cui i test a fixture fanno da regressione quando il sito fa restyling.

---

## Convenzioni comuni a tutti i connettori

- **Un file per cinema** in `scraper/scraper/connectors/<slug>.py`, classe
  `<Nome>Connector(BaseConnector)`.
- `scrape()` **non solleva** per errori di rete/parsing: raccoglie in `ScrapeResult.errors`
  con `make_error(...)`. Vale sempre `base.py`.
- HTTP con `retry_request(...)` da `scraper/http.py` (backoff, 403 non ritentato).
- Header: `Accept-Language: it-IT`.

### User-Agent (decisione da prendere, non ignorarla)

`AGENTS.md` impone uno **User-Agent identificabile** del progetto:

```
CinePosto/1.0 (+https://github.com/Jysek/CinePosto; 55837328+Jysek@users.noreply.github.com)
```

La ricognizione del 19/09/2026 ha usato questo UA e tutti e 5 i siti hanno risposto `200`:
per i **nuovi connettori usa questo**. ⚠️ I connettori esistenti (`postmodernissimo.py`,
`thespace.py`, `uci.py`) usano invece `DEFAULT_USER_AGENT`, che è uno UA Chrome: è una
**discrepanza pre-esistente** con `AGENTS.md`. Non risolverla in queste sessioni (rischio di
rompere fonti che funzionano); limitati a segnalarla. Se in futuro si uniforma, `DEFAULT_USER_AGENT`
va sostituito con lo UA del progetto in un commit dedicato.
- Costanti (URL, nomi, slug, venue id) in `scraper/scraper/config.py`, mai hardcoded.
- Coordinate e indirizzo in `CINEMA_LOCATIONS` (slug = chiave del DB).
- Registrazione in `scraper/scraper/main.py` nella lista `connectors`.
- Test in `scraper/tests/test_<slug>.py`, nomi che **descrivono il comportamento**.
- A fine lavoro: aggiornare la riga del cinema in `docs/scraper/copertura.md`
  (🟢 → ✅) **nello stesso commit**, e `make lint` + `make test-scraper` verdi.

## Definizione di "fonte verificata" (perché queste 5)

Nella ricognizione del 19/09/2026 questi siti hanno: sito raggiungibile, `robots.txt`
consultato e non ostativo, e una fonte di orari **leggibile staticamente** (JSON-LD,
microdata o API). Le schede qui sotto fissano il contratto tecnico; la ricognizione
completa sta in [`../copertura.md`](../copertura.md).
