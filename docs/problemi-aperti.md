# CinePosto — Problemi aperti

> Verificato su `5c53fd5` (`2026-09-23`).

**Come si usa questo file.** Qui finisce tutto ciò che **oggi non funziona** o non è ancora
coperto, con la prova che lo dimostra. Quando un problema si risolve, **la voce si cancella**:
niente "risolto il…", niente voci barrate. La storia sta solo in `stato-e-diario.md`. Questo file
non è una roadmap: le cose da fare che non sono difetti stanno in `README.md` (roadmap) e in
`scraper/copertura.md` (sale non coperte).

## Formato di una voce

### <titolo breve>
**Dove**: `<file>:<riga>` · **Prova**: `<comando>` → `<esito>` · **Data**: `<data>`
Una o due righe: cosa dovrebbe succedere e cosa succede invece.

## Voci aperte

### I residui di run passate restano nel DB: «Talking Tom Heroes» compare in due schede
**Dove**: `backend/app/seed_from_json.py` (nessuna riga non più nei JSON viene rimossa) · **Prova**:
`curl -s http://localhost:8000/api/v1/film/oggi` → 23 film, fra cui #42 «TALKING TOM HEROES SUPER
AMICI AL CINEMA» e #53 «Talking Tom Heroes - Super amici» (stesso film) · **Data**: `2026-09-23`
Nei JSON la coppia non esiste (una sola forma: `grep -c '"id": "Talking' scraper/output/films.json` → 1), ma
il seed non rimuove le righe accumulate dalle run passate: i residui hanno ancora showings nella
finestra e nell'app tornano schede doppie. Le varianti di titolo fra fonti della run corrente si
uniscono ora nello scraper (alias + fusione per `wikidata_id`); qui resta la pulizia del DB: serve
il purge del seed, oppure `python -m app.maintenance.dedup_films --merge 42:53 --apply`.

### Un sequel con numero romano può essere fuso con il primo film
**Dove**: `scraper/scraper/normalizer.py` (`fuzzy_match`, ramo di contenimento) · **Prova**:
`fuzzy_match("Rocky II", "Rocky")` → `True` (le chiavi `rockyii`/`rocky`, la prima contiene la
seconda) · **Data**: `2026-09-23`
La guardia sulle cifre finali protegge «Amori e incantesimi 2» dai numeri arabi, non i numeri
romani («Rocky II») né i titoli che contengono l'altro («Dune»/«Dune Part Two», caso voluto dal
test di contenimento). `_ROMAN_NUM_SUFFIX` (`normalizer.py`) è compilato ma mai applicato:
decidere se usarlo (con un test che «Rocky II» resta «Rocky II») o eliminarlo.

### L'arricchimento Wikidata non aggancia i titoli "urlati" o delle riedizioni
**Dove**: `scraper/scraper/metadata.py` (`_search_fuzzy` / `enrich_film`) · **Prova**:
`scraper/.wikidata_cache.json` → `"cars - 20esimo anniversario" → "__NOT_FOUND__"`; in
`scraper/output/films.json` la forma «CARS - MOTORI RUGGENTI - 20MO ANNIVERSARIO» ha
`wikidata_id: null` · **Data**: `2026-09-23`
Entrambe le forme della riedizione del 20° anniversario di *Cars* restano senza entità: se la
trovassero, la fusione per `wikidata_id` le unirebbe senza bisogno di alias. È il motivo per cui
`title_aliases.py` esiste (soluzione ripiegata, non quella giusta): migliorare la ricerca
dell'entità (titolo originale, anno), poi la voce di alias potrà sparire.

### La tab bar di React Navigation usa la prop pointerEvents deprecata su web
**Dove**: `node_modules/@react-navigation/bottom-tabs/src/views/BottomTabBar.tsx:385` e
`BottomTabView.tsx:326` · **Prova**: avvio del dev server (`npx expo start --web`) + console del
client web → `props.pointerEvents is deprecated. Use style.pointerEvents` · **Data**: `2026-09-23`
react-native-web 0.21 depreca la prop `pointerEvents` delle View in favore di `style.pointerEvents`.
La tab bar di React Navigation 7 la passa ancora come prop (`pointerEvents={isTabBarHidden ? 'none' :
'auto'}`), quindi la console web del dev server mostra un warning che non viene dal nostro codice:
l'istanza nostra (`app/src/screens/FilmsTab.js`) è stata corretta nella stessa data. Si risolve con un
upgrade di react-navigation che converta la prop in stile; non si patcha `node_modules`.

### L'app non avverte quando i dati sono vecchi
**Dove**: `app/src/api/api.js` · **Prova**: `grep -rn "latest_scraped\|dati non aggiornati" app/src` → nessun risultato · **Data**: `2026-09-21`
Se lo scraping notturno fallisce, l'app mostra la programmazione vecchia senza dirlo all'utente.
La data dell'ultimo aggiornamento esiste solo in `GET /api/v1/admin/dataset-info`
(`backend/app/routers/admin.py:53`), protetto da token admin e non consumato dall'app: serve un
dato pubblico (o un endpoint) su cui costruire l'avviso.
