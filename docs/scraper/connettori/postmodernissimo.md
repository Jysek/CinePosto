# PostModernissimo — scheda connettore

> Verificato su `071b125` (`2026-09-25`): connettore, test e ordine delle fonti di testo
> confrontati col codice. Il markup del sito osservato l'ultima volta in una run reale non è
> stato ri-verificato in questa sessione (nessuno scraping live).

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

## 4. Fonte secondaria: card HTML

`_parse_film_cards` legge `ul.movie-container > li.movie-item` per i poster (`<img>`) e come
base di ripiego se il RSC è vuoto (`_fallback_from_html`, senza orari: il delta conserva quelli
della run precedente). I poster non sono nel RSC.

## 5. Riconciliazione con la pagina di dettaglio

La pagina di dettaglio è la fonte canonica degli **orari** (la homepage passa da una edge-cache
che può restare indietro di ore). `_reconcile_with_detail` confronta la firma degli show e
sostituisce quelli della homepage se differiscono; se il dettaglio non è disponibile si tengono
i dati della homepage.

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

- `scraper/tests/test_postmodernissimo.py` — parsing RSC, direttore, filtri evento/weekend;
- `scraper/tests/test_postmodernissimo_description.py` — ordine delle fonti di testo, non-degrado,
  dettaglio che fallisce senza rompere la run;
- `scraper/tests/test_postmod_detail_reconcile.py` — il dettaglio vince sulla homepage per gli orari.
