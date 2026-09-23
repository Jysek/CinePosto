# CinePosto — Problemi aperti

> Verificato su `857c68b` (`2026-09-24`).

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

### `make prod-down` fallisce senza le variabili d'ambiente di produzione
**Dove**: `Makefile:103` (`prod-down`) · **Prova**: `make prod-test` → `exit=0` e `curl -k https://localhost:8443/health` → `{"status":"ok"}`; subito dopo `make prod-down` → `error while interpolating services.backend.environment.ADMIN_TOKEN: required variable ADMIN_TOKEN is missing a value` · **Data**: `2026-09-24`
`prod-up`/`prod-test` inlineano le variabili obbligatorie, `prod-down` no: il compose rifiuta
di interpolare e il make fallisce con exit 2. La chiusura funziona solo ripassando a mano
`ADMIN_TOKEN` e `CORS_ORIGINS` (o qualsiasi valore, sono usati solo per l'interpolazione).
Fix possibile nel Makefile: inlineare le stesse variabili di `prod-test` anche in `prod-down`.

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
