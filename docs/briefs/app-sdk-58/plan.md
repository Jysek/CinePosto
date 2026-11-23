# Piano — upgrade Expo SDK 58

> Contratto: [`plan-brief.md`](plan-brief.md). Classe `L`. Stile: `full`.
> Verificato su `fefe097` (`2026-11-23`).

## How to resume

- Branch di lavoro del ciclo: `chore/app-sdk-58`, creato da `main` **dopo** il commit del
  palinsesto (blocco 1). Il branch `fix/scraper-postmod-guard-slug` non si tocca.
- Riga di stato: `grep '| Stato: TODO' docs/briefs/app-sdk-58/plan.md` — si parte dal primo
  la cui condizione e' vera. `N/A` non si esegue.
- Gate app (da `.github/workflows/ci.yml`, job *App*): `npx expo export --platform web` e
  `npx expo-doctor@latest`, dentro `app/`. Gate backend/scraper: `make test`,
  `make test-scraper` (Docker).
- Trappola 1: `scripts/check-app-web.sh` pretende il backend su (`make up && make seed`,
  adesso e' healthy) e `http://localhost:3000` in `CORS_ORIGINS` del backend.
- Trappola 2: `npm install` tocca `node_modules` condiviso: un solo writer per volta. Il
  padre installa, i figli non lanciano mai npm.
- Trappola 3: `expo-status-bar` 58 non ha `backgroundColor`/`translucent` — la correzione e'
  togliere le prop, non spostarle di libreria.
- Primo blocco da eseguire in assenza di commit: il **2** (branch + commit di questo piano).

## Blocchi

1. Commit del palinsesto raccolto oggi e push di `main` | files: scraper/output/cinemas.json,scraper/output/films.json,scraper/output/movies.json,scraper/output/showings.json | done: `make test` verde (95) e commit `chore(scraper)` su `main` con solo quei 4 path | Stato: DONE
2. Branch `chore/app-sdk-58` da `main` e commit del contratto | files: docs/briefs/app-sdk-58/plan-brief.md,docs/briefs/app-sdk-58/plan.md | done: commit esiste sul branch e l'albero e' pulito | Stato: DONE
3. Upgrade dipendenze allineate a SDK 58 | files: app/package.json,app/package-lock.json | done: `expo ~58.0.26`, `react-native 0.88.1`, `react 19.3.0`, `react-dom 19.3.0`, `react-native-web ~0.21.4`, `screens ~4.30.1`, `safe-area-context ~5.11.1`, `webview 14.0.1`, pacchetti `expo-*` a `~58.x`; `npx expo install --check` senza segnalazioni | Stato: DONE
4. Icone alla major nuova, solo se un controllo si lamenta | files: app/package.json,app/package-lock.json | done: `expo-doctor` tutti i check verdi (senza il salto o con); se nessuno si lamenta -> `N/A` | Stato: N/A
5. Barra di stato: togliere `backgroundColor` e `translucent` dalle tre schermate | files: app/src/screens/FilmsTab.js,app/src/screens/LocationTab.js,app/src/screens/SearchTab.js | done: `grep -n "translucent\|StatusBar backgroundColor" app/src/screens/*.js` vuoto, `npx expo export --platform web` verde | Stato: DONE
6. Verifica completa: export, doctor, harness web, giro visivo in browser | files: nessuno | done: checklist di `scripts/check-app-web.sh` soddisfatta (home carica, filtro 8 cinema, località 8 righe + 8 marker senza pin rotti, dettaglio leggibile) e `expo-doctor` tutti i check verdi | Stato: TODO
7. Se l'export web si rompe per il deep import del codegen, estendere lo shim Metro | files: app/metro.config.js,app/shims/codegenNativeComponent.web.js | done: export web verde; se non serve -> `N/A` | Stato: TODO
8. Documenti allineati a SDK 58 | files: AGENTS.md,README.md,docs/app/overview.md,docs/development.md,docs/development-windows.md,docs/panoramica.md,docs/stato-e-diario.md | done: `grep -rn "SDK 57\|0\.86" AGENTS.md README.md docs/*.md docs/app/overview.md` vuoto (esclusa la cronologia in `stato-e-diario.md`), nota Expo Go e tabella stack aggiornate con le versioni reali, riga di diario in coda | Stato: TODO
9. Review a tre angoli, fix accettate, push del branch | files: nessuno | done: P0/P1 chiusi o motivati, gate verde, `git push -u origin chore/app-sdk-58` | Stato: TODO

## Lanes

- **lane-deps** (`shared` fra 3 e 4, un solo writer = **padre**): `app/package.json`,
  `app/package-lock.json`. Nessun figlio lancia npm: `node_modules` e' condiviso.
- **lane-codice** (1 `worker`, parte insieme a `lane-deps`): `app/src/screens/FilmsTab.js`,
  `app/src/screens/LocationTab.js`, `app/src/screens/SearchTab.js` (blocco 5). File disgiunti
  da `lane-deps`, nessuna dipendenza: l'edit e' una riga per schermata e non richiede la
  nuova SDK installata.
- **lane-docs-a** (1 `worker`, dopo il blocco 3 per avere le versioni reali): `AGENTS.md`,
  `README.md`, `docs/panoramica.md`.
- **lane-docs-b** (1 `worker`, dopo il blocco 3): `docs/app/overview.md`,
  `docs/development.md`, `docs/development-windows.md`.
- **shared** (padre): `docs/stato-e-diario.md`, `docs/briefs/app-sdk-58/*.md`.

Ondate: **1** = `lane-deps` (padre) + `lane-codice` (figlio) in parallelo; **2** =
verifica (padre) + `lane-docs-a` + `lane-docs-b` in parallelo; **3** = review. Budget per
ondata: 25 minuti di orologio (classe `L`: 60), tetto del ciclo 90 minuti.
