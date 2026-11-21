# PostModernissimo — scheda connettore

> Verificato su `aa3be46` (`2026-11-20`): risoluzione del permalink `/extra/` sulla pagina
> `/films/`, riparazione dei JSON dell'ultima run. Il markup del sito è stato osservato in una run
> reale del 2026-11-20; nessuna richiesta live in questa sessione.

> **Stato**: 🟢 in produzione, connettore storico · Perugia (PG) · Nessuna autenticazione.
> Il comportamento tecnico generale è in [`../architecture.md`](../architecture.md#postmodernissimo);
> questa scheda fissa il *contratto*: dove stanno i dati, cosa si estrae e in che ordine.

## 1. Identità

| Campo | Valore |
|---|---|
| Nome pubblico | **PostModernissimo** |
| Slug | `postmodernissimo` |
| Comune | Perugia (PG) |
| Sito | `https://www.postmodernissimo.com` |
| E-commerce | assente: `buy_url` è sempre `null` per questa sala |
| Costanti | `POSTMOD_CINEMA_NAME`, `POSTMOD_CINEMA_SLUG`, `POSTMOD_CINEMA_URL` in `scraper/scraper/config.py` |

## 2. Etica / scraping

Vale il [`NOTICE`](../../../NOTICE) del progetto: una run al giorno (03:00, timer systemd),
User-Agent identificabile, dati pubblici di programmazione. In sviluppo non si lancia il live:
i JSON committati sono le fixture. `robots.txt` non introduce vincoli aggiuntivi oltre alla
regola generale.

## 3. Fonte primaria: payload RSC (Next.js)

La homepage è una pagina Next.js con React Server Components: i dati sono incapsulati in
script `self.__next_f.push([1,"…"])`. `_parse_rsc_payload` prende il chunk più grande, lo
unescapa (solo `\"` e `\\`) e trova i film col regex
`{"id":N,"title":"…","slug":"…","permalink":"…"}`. Per ogni match, con brace-matching locale e
finestre di ricerca, estrae:

| Campo | Helper | Finestra | Contenuto |
|---|---|---|---|
| `content` | `_extract_content` | +3000 char | **sinossi intera**, stringa JSON |
| `details` | `_extract_details` | +3000 char | `genere`, `regia`, `durata`, `youtube_cover` |
| `shows` | `_extract_shows` | +5000 / array +20000 char | `date` (`YYYYMMDD`), `orario`, `opzioni` |

Lo stesso `permalink` può comparire più volte nello stream: gli show si accumulano senza
duplicati e, per la `content`, si tiene la variante **più completa** (mai una più corta o tronca).

**Route `/extra/` (dal 2026-11-10 circa non esiste più).** Il sito espone le proiezioni delle
rassegne anche sotto `…/extra/<slug>`, che risponde 404, dentro un record che porta un oggetto
`movie` annidato con il permalink buono `…/films/<slug>`. Il parser risolve quindi il permalink
**prima** di usarlo come chiave: se contiene `/extra/` prende il primo permalink `/films/`
successivo al match con lo stesso slug; se la risoluzione fallisce ma lo stesso slug ricompare
più avanti come record `/films/`, la fusione completa il permalink dal record successivo,
altrimenti il record resta senza link. Effetti: le due
voci dello stesso film (una `/extra/`, una `/films/`) si fondono in un solo film con gli show
accumulati; `source_url` punta sempre a una pagina che risponde 200; nessuna richiesta parte
mai verso `/extra/`, quindi la run non produce più due errori `detail` spurii. Gli orari restano
anche quando la pagina film non c'è: la proiezione esce con `source_url` assente, perché gli
orari sono veri e altrimenti persi.

## 4. Fonte secondaria: card HTML

`_parse_film_cards` legge `ul.movie-container > li.movie-item` per i poster (`<img>`) e come
base di ripiego se il RSC è vuoto (`_fallback_from_html`, senza orari: il delta conserva quelli
della run precedente). I poster non sono nel RSC.

## 5. Riconciliazione con la pagina di dettaglio

La pagina di dettaglio è la fonte canonica degli **orari** (la homepage passa da una edge-cache
che può restare indietro di ore). `_reconcile_with_detail` confronta la firma degli show e
sostituisce quelli della homepage se differiscono; se il dettaglio non è disponibile si tengono
i dati della homepage. Il dettaglio si chiede solo a un permalink che risponde 200: un record
senza link (vedi §3, route `/extra/`) viene saltato, non inseguito.

## 6. Sinossi: ordine delle fonti (dal più completo al più debole)

1. **`content` del payload RSC** — la sinossi intera, dato strutturato (scelta preferita):
   prima quello della homepage, poi, se manca, quello della pagina di dettaglio (voce col
   giusto slug, per non prendere un film correlato);
2. **primo paragrafo della pagina di dettaglio** (`article p, .film-content p, .description p`);
3. **`<meta name="description">`** — il CMS la tronca a ~100 caratteri a metà parola: è
   l'ultima spiaggia, si usa così com'è, senza inventare il testo mancante.

Il dettaglio irraggiungibile non rompe la run: `fetch_film_detail` raccoglie l'errore in
`ScrapeResult.errors` (fase `detail`) e il film resta con la descrizione del payload, se c'è.

## 7. Non-degrado fra run

`pick_fuller_description` (in `scraper/scraper/normalizer.py`) sceglie fra due descrizioni
quella non troncata, e a pari troncamento la più lunga. È usata quando il delta riconcilia con
la run precedente e quando si fondono varianti dello stesso film: una sinossi intera non si
sovrascrive con una meta description troncata.

## 8. Test

- `scraper/tests/test_postmodernissimo.py` — parsing RSC, direttore, filtri evento/weekend,
  risoluzione del permalink `/extra/` (fusione delle due voci, record senza pagina film tenuto con
  `source_url` assente, nessuna richiesta verso `/extra/`, slug non combaciante non risolto,
  risoluzione fuori finestra completata dalla fusione con il record `/films/` successivo);
- `scraper/tests/test_postmodernissimo_description.py` — ordine delle fonti di testo, non-degrado,
  dettaglio che fallisce senza rompere la run;
- `scraper/tests/test_postmod_detail_reconcile.py` — il dettaglio vince sulla homepage per gli orari.
