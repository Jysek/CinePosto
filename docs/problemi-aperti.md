# CinePosto — Problemi aperti

> Verificato su `9dc8fc1` (`2026-09-23`).

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

### Lo stesso film compare due volte nell'app (varianti di titolo fra fonti, residui di run)
**Dove**: `backend/app/maintenance/dedup_films.py` (regole di fusione) · **Prova**:
`docker compose run --rm backend python -m app.maintenance.dedup_films` → candidato
#53 «Talking Tom Heroes - Super amici» ↔ #42 «TALKING TOM HEROES SUPER AMICI AL CINEMA» (una è
l'altra più un suffisso di parole); inoltre `films` id 29 `CARS - MOTORI RUGGENTI - 20MO
ANNIVERSARIO` (anno NULL, 26 showings) e id 68 `Cars – 20esimo anniversario` (`year=2006`, 2
showings) sono lo stesso film · **Data**: `2026-09-23`
La classe `&`/`e` + maiuscole + anno NULL è **chiusa**: la chiave naturale del backend fonde `&`
in `e` e adotta l'anno NULL, e lo script di manutenzione ha fuso le righe già accumulate (40/52).
Restano due classi che nessuna regola sulle stringhe unisce in sicurezza: (2) **varianti di titolo
italiano fra fonti diverse** (29/68, 42/53) — si approvano a mano con `--merge` o si chiudono con
un merge cross-fonte nello scraper; (3) **residui di run passate** non più nei JSON — servono
guardie proprie, non la fusione.

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
