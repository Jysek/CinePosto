# Cinema in Umbria — registro di copertura e progresso

> Verificato su `0c56a7e` (`2026-09-21`): intestazione aggiunta, contenuto non ancora ricontrollato.

> **Documento di lavoro.** Serve a sapere *tutte* le sale dell'Umbria prima di scrivere i
> connettori, e a tracciare cosa è implementato e cosa no. Va aggiornato **nello stesso commit**
> in cui si aggiunge o si toglie una sala (regola di `AGENTS.md`).
>
> Ultima ricognizione: **19 settembre 2026**.
> Legenda stato: ✅ implementato · 🟢 fonte verificata, pronto per il connettore · 🟠 sito noto,
> tecnica da analizzare · 🔵 identità o sito da verificare · ⛔ escluso (motivo indicato).

## Riepilogo

| Metrica | Valore |
|---|---|
| Comuni dell'Umbria | 92 |
| Comuni con almeno una sala nota | 21 |
| Comuni senza sala nota | 71 |
| **Sale implementate** | **8** |
| Sale con fonte verificata, pronte per il connettore | 0 |
| Sale con sito noto, tecnica da analizzare | 11 |
| Sale con identità o sito da verificare | 11 |
| Sale escluse con motivazione | 8 |

## Metodo

1. **Elenco sale**: unione di tre fonti incrociate —
   [ANEC Umbria](https://www.umbriacinema.it/) (sale associate),
   **OpenStreetMap/Overpass** (`amenity=cinema` in Umbria, con coordinate),
   ricerche web per comune.
2. **Elenco comuni**: confini amministrativi `admin_level=8` da OSM → 92 comuni, l'elenco
   ufficiale usato nell'ultima sezione.
3. **Verifica per ogni sala**: raggiungibilità del sito, `robots.txt`, sitemap, tipo di fonte
   (HTML, microdata schema.org, API), sempre con lo User-Agent identificabile del progetto:
   `CinePosto/1.0 (+https://github.com/Jysek/CinePosto; 55837328+Jysek@users.noreply.github.com)`.
4. **Nessuno scraping ripetuto**: solo singole richieste di verifica su pagine pubbliche.

## Sale dell'Umbria — stato di implementazione

| # | Sala | Comune | Prov. | Sito | robots.txt | Fonte / tecnica | Stato |
|---|---|---|---|---|---|---|---|
| 1 | PostModernissimo | Perugia | PG | postmodernissimo.com | consentito | payload RSC + HTML | ✅ |
| 2 | The Space Cinema Corciano | Corciano | PG | thespacecinema.it | consentito | API REST OAuth2 (venue 1027) | ✅ |
| 3 | UCI Cinemas Perugia | Perugia | PG | ucicinemas.it | consentito | API JSON (Cloud Run) | ✅ |
| 4 | Cinema Zenith | Perugia | PG | cinemazenith.it | `Disallow:` vuoto → ok | JSON-LD schema.org (fallback microdata settimana) | ✅ |
| 5 | Nuovo Cinema Castello | Città di Castello | PG | nuovocinemacastello.it | ok | JSON-LD schema.org (tema `zen25`, come Zenith) | ✅ |
| 6 | Cinema Metropolis | Umbertide | PG | cinemametropolis.it | ok | microdata schema.org `startDate` (homepage → `/films/<slug>/`) | ✅ |
| 7 | Cinema Teatro Concordia | Marsciano | PG | cineconcordia.it | ok | microdata schema.org `startDate` | ✅ |
| 8 | The Space Cinema Terni | Terni | TR | thespacecinema.it | ok | API REST microservice (venue 1006) | ✅ |
| 9 | Nuovo Cinema Méliès | Perugia | PG | cinegatti.it | ok | orari non nel markup statico | 🟠 |
| 10 | Sant'Angelo Cinematografo | Perugia | PG | cinegatti.it | ok | da determinare | 🟠 |
| 11 | Cinema Astra | Gubbio | PG | cinemaastra.com | ok | da determinare (`/movies/`) | 🟠 |
| 12 | Cinema Esperia | Bastia Umbra | PG | cinemaesperiabastia.it | ok | markup `timeslot`, no microdata | 🟠 |
| 13 | Nuovo Cinema Caporali | Castiglione del Lago | PG | nuovocinemacaporali.it | ok | da determinare | 🟠 |
| 14 | Multisala Politeama Clarici | Foligno | PG | cinemaclarici.it | ok (`/kubrick/` escluso) | da determinare | 🟠 |
| 15 | Multisala Supercinema Clarici | Foligno | PG | cinemaclarici.it | ok | da determinare | 🟠 |
| 16 | Cinema Sala Frau | Spoleto | PG | cinemasalafrau.it | ok | da determinare | 🟠 |
| 17 | Cinéma Sala Pegasus | Spoleto | PG | cinemasalapegasus.wordpress.com | da verificare | da determinare | 🟠 |
| 18 | Cinema Nido dell'Aquila | Todi | PG | cinemanidodellaquila.it | ok | da determinare | 🟠 |
| 19 | Cinema Mario Monicelli | Narni | TR | cinemanarni.com | ok | da determinare (sala comunale) | 🟠 |
| 20 | Cinema Pavone | Perugia | PG | — | — | solo OSM: forse non più attivo | 🔵 |
| 21 | Cinema Eden | Città di Castello | PG | cinemaeden.it (da confermare) | da verificare | città e attività da confermare | 🔵 |
| 22 | Cinema Ed Lewis | Montone | PG | — | — | solo OSM: natura da chiarire | 🔵 |
| 23 | Cinema Teatro Don Bosco | Gualdo Tadino | PG | educareallavitabuona.it | ⚠️ errore TLS 525 | fonte instabile | 🔵 |
| 24 | Cinema Teatro Astra | San Giustino | PG | — | — | solo OSM: sito da trovare | 🔵 |
| 25 | Cityplex Politeama Lucioli | Terni | TR | cinematernipoliteama.it | — | sito non raggiungibile | 🔵 |
| 26 | Cinema Corso | Orvieto | TR | (link ANEC non aggiornato) | — | da chiarire se attivo e con quale sito | 🔵 |
| 27 | Nuovo Cinema Carpine | Magione | PG | — | — | nessun sito proprio trovato | 🔵 |
| 28 | Cinema Carovana | Norcia | PG | — | — | nessun sito proprio trovato | 🔵 |
| 29 | Sala multimediale | Cascia | PG | — | — | solo OSM: da verificare | 🔵 |
| 30 | Palazzo del Monte Frumentario | Assisi | PG | — | — | da verificare se cinema permanente | 🔵 |

## Escluse con motivazione

| Sala / voce | Motivo |
|---|---|
| **Cinema Castello** (`cinemacastello.it`) | È a **Firenze** (via Reginaldo Giuliani 374), non in Umbria. Non va aggiunto. |
| **CineTuscia Village** | Il link ANEC di Orvieto rimanda a un cinema di **Viterbo/Vitorchiano (Lazio)**. |
| **Cinema Perla** | OSM lo marca **chiuso** (`disused:amenity=cinema`). |
| **Spello** | Nessuna sala permanente: solo rassegne estive e il Festival del Cinema di Spello. |
| **Passignano Super Cinema Estate** | Arena all'aperto **stagionale** (estate). |
| **Frontone Cinema all'aperto** (cinegatti.it) | Arena **stagionale**. |
| **Arene estive in genere** | Copertura sensata ma **dopo** le sale stabili. |
| **Multiplex 2000** (`multiplex2000.it`) | Comune non identificabile dal sito: da chiarire, probabilmente fuori Umbria. |

## Comuni senza sala nota (71)

Nessuna sala trovata in questi comuni con le tre fonti. Non è una prova definitiva di assenza
(una sala senza sito web non è copribile comunque), ma è l'elenco da spuntare se si vuole
chiudere la ricognizione al 100%:

Acquasparta, Allerona, Alviano, Amelia, Arrone, Attigliano, Avigliano Umbro, Baschi, Bettona,
Bevagna, Calvi dell'Umbria, Campello sul Clitunno, Cannara, Castel Giorgio, Castel Ritaldi,
Castel Viscardo, Cerreto di Spoleto, Citerna, Città della Pieve, Collazzone, Costacciaro, Deruta,
Fabro, Ferentillo, Ficulle, Fossato di Vico, Fratta Todina, Giano dell'Umbria, Giove,
Gualdo Cattaneo, Guardea, Lisciano Niccone, Lugnano in Teverina, Massa Martana,
Monte Castello di Vibio, Monte Santa Maria Tiberina, Montecastrilli, Montecchio, Montefalco,
Montefranco, Montegabbione, Monteleone d'Orvieto, Monteleone di Spoleto, Nocera Umbra, Otricoli,
Paciano, Panicale, Parrano, Penna in Teverina, Piegaro, Pietralunga, Poggiodomo, Polino, Porano,
Preci, San Gemini, San Venanzo, Sant'Anatolia di Narco, Scheggia e Pascelupo, Scheggino, Sellano,
Sigillo, Stroncone, Torgiano, Trevi, Tuoro sul Trasimeno, Valfabbrica, Vallo di Nera, Valtopina.

## La scorciatoia che riduce il lavoro

Le sale **Zenith, Nuovo Cinema Castello, Concordia e Metropolis** usano lo stesso vocabolario di
dati: gli spettacoli sono marcati con [schema.org](https://schema.org/ScreeningEvent)
`Movie` + `ScreeningEvent`. **Attenzione alla forma**, che non è unica (verificato 19/09/2026):
Zenith e Castello espongono la settimana in **JSON-LD** `@graph` nella homepage; Concordia in
**microdata** con `div[itemprop=startDate][content]`; Metropolis in **microdata** ma solo sulle
pagine `/films/<slug>/` (la homepage non ha orari). Dettagli in [`connettori/`](connettori/README.md).

```html
<div itemscope itemtype="http://schema.org/Movie" itemid="https://.../film/<slug>/">
  <span itemprop="name">Titolo</span>
  ...
  <div itemscope itemtype="http://schema.org/ScreeningEvent">
    <meta itemprop="workPresented" content="Titolo">
    <time datetime="2026-09-19T17:15:00+02:00" itemprop="startDate">17:15</time>
  </div>
</div>
```

I temi CSS sono diversi (`zen25`, `postmetro`, `concordia`…) e le classi pure (`pw_row`,
`pw_show`): **il parser deve agganciarsi ai microdata, non alle classi del tema**. Così un solo
connettore parametrizzato copre più cinema (DRY) invece di N connettori quasi identici.

## Prossime ondate

Le schede di implementazione pronte per una sessione nuova sono in
[`connettori/`](connettori/README.md): una per ciascuna sala 🟢, con markup reale, URL,
insidie e test da scrivere. **Ordine e file da allegare per ogni sessione:**
[`connettori/README.md#ordine-di-esecuzione-obbligatorio`](connettori/README.md#ordine-di-esecuzione-obbligatorio).
In sintesi: l'**ondata 0 (Zenith)** fa nascere l'estrattore `SchemaOrgExtractor` e va mergiata
per prima; Castello, Concordia e Metropolis sono adattatori che la riusano; **The Space Terni**
è indipendente e si può fare in qualsiasi momento.

| Ondata | Contenuto | Sale coperte dopo |
|---|---|---|
| **0** | Connettore "schema.org microdata" + Zenith come pilota, con test | 4 |
| **1** | Stessa famiglia: Castello, Concordia, Metropolis — più The Space Terni (indipendente, refactor `thespace.py`) | 8 |
| **2** | Analisi e connettori: Clarici ×2, Astra, Caporali, Esperia, Méliès, S. Angelo, Nido dell'Aquila, Monicelli, Sala Frau, Pegasus | 19 |
| **3** | Chiarimento 🔵 (siti mancanti, sale comunali, fonti instabili) + comuni ancora senza sala | 19–25 |

Ogni ondata: aggiornare **questo documento**, `scraper/scraper/config.py` (costanti e
`CINEMA_LOCATIONS`), `scraper/scraper/main.py` (registrazione), aggiungere i test in
`scraper/tests/`, e verificare `validate_output.py`.
