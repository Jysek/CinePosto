# CinePosto — Problemi aperti

> Verificato su `a360d5a` (`2026-09-25`): cancellata la voce sui residui del DB (risolta con
> l'archiviazione `removed_at`), aggiunta quella sul rischio `wikidata_id` del seed (riprodotto in
> memoria). Le altre voci non sono state ricontrollate in questa sessione.

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

### Il seed può esplodere (o creare un doppione) quando un film torna con un titolo nuovo
**Dove**: `backend/app/repositories/film_repo.py:101` (`upsert_from_scraper`: lookup solo per chiave
naturale) e `:135` (scrive `wikidata_id` anche quando è già di un'altra riga) · **Prova**:
`docker compose run --rm backend python -c "from sqlalchemy import create_engine; from sqlalchemy.orm
import sessionmaker; from app.database import Base; from app.models import Film; from app.repositories
import film_repo; e = create_engine('sqlite:///:memory:'); Base.metadata.create_all(e); db =
sessionmaker(bind=e)(); film_repo.upsert_from_scraper(db, {'title': 'A', 'wikidata_id': 'Q1'});
db.commit(); film_repo.upsert_from_scraper(db, {'title': 'B', 'wikidata_id': 'Q1'}); db.commit()"` →
`IntegrityError: UNIQUE constraint failed: films.wikidata_id` · **Data**: `2026-09-25`
Se un film torna in programmazione con una forma di titolo che non incontra la chiave naturale ma
con lo stesso `wikidata_id` di una riga già nel DB (anche archiviata), l'upsert prova l'INSERT e
viola `UNIQUE(wikidata_id)`: `make seed` si ferma e il DB non si aggiorna. Stesso esito se il
`wikidata_id` arriva in aggiornamento su una riga che non lo possiede. Nessun caso reale oggi (0
coppie in conflitto sul DB del 25/09), ma la fase-16 lascia le righe archiviate con i loro
`wikidata_id` e la probabilità cresce. Soluzione pianificata: `pianificazione/fase-21` (guardia di
identità a due segnali, mai crash, invariante di fine seed).

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
