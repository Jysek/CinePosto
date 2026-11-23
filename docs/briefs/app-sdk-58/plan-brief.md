# Brief — upgrade Expo SDK 58

> Verificato su `fefe097` (`2026-11-23`). Classe `L`, stile `full`.
> Piano: [`plan.md`](plan.md).

## Obiettivo

Portare l'app da **Expo SDK 57** (React Native 0.86.3, React 19.2.3) a **SDK 58**
(React Native 0.88.1, React 19.3.0), senza cambiare comportamento ne' aspetto:
stesse schermate, stessi dati dall'API, stessa versione web e nativa. La documentazione
che dichiara la versione dell'SDK si allinea nello stesso ciclo.

## Vincoli

- App in **JavaScript puro**: la rottura "Strict TypeScript API" di React Native 0.87
  non si applica (nessun `.ts`, nessun deep import tipizzato nel nostro codice).
- Versioni da `bundledNativeModules` di `expo@58.0.26`: `react-native` 0.88.1,
  `react`/`react-dom` 19.3.0, `react-native-web` ~0.21.4, `react-native-screens` ~4.30.1,
  `react-native-safe-area-context` ~5.11.1, `react-native-webview` **14.0.1**,
  `expo-asset` ~58.0.21, `expo-font` ~58.0.12, `expo-splash-screen` ~58.0.14,
  `expo-status-bar` ~58.0.5, `expo-linear-gradient` ~58.0.4.
- Node richiesto dal tooling SDK 58: >= 22.13 sulla linea 22 (locale 24.22.1, CI `node 22`).
- WebView nativa: salto di major obbligato (13.16.1 -> 14.0.1). Sul web la mappa usa un
  `<iframe>`, quindi l'export web non esercita la WebView nativa.
- Nessuno scraping live in questo ciclo.
- Italiano in commenti, commit e documenti.
- **Fuori scope**: `npx expo prebuild`, rigenerazione delle cartelle native (non esistono),
  Expo Router, migrazione a TypeScript, `expo-file-system`/`expo-notifications` (non usati).

## Decisioni chiuse (domanda -> risposta)

1. **Versione da atterrare?** -> L'ultima patch della linea 58 (**58.0.26**), non 58.0.0:
   stessa cosa per i documenti, meno patch manuali dopo. (a)
2. **Quanto a fondo la verifica?** -> Build web + controlli automatici + **giro visivo in
   browser** sulle quattro schermate (home, filtro cinema, località con mappa, dettaglio
   film) col backend acceso. (a)
3. **Le librerie native fuori dal controllo di Expo?** -> WebView alla major nuova
   (obbligata dai controlli automatici); icone solo se `expo-doctor` o l'export si
   lamentano, altrimenti quel passo si chiude `N/A`. (a)
4. **La barra di stato con le due opzioni rimosse da React Native 0.88?** -> Rimuoverle da
   **tutte e tre** le schermate che le usano (home film, cerca, località). Verificato che
   `expo-status-bar` 58 **non** le supporta: l'opzione "passare alla libreria Expo" avrebbe
   dato lo stesso risultato con un import in più. (a, dopo correzione)
5. **I quattro file di palinsesto non committati?** -> Sono la raccolta di oggi 13:43 (8
   cinema, finestra 23->30 novembre, 283 spettacoli, 31 film, validazione verde). Si
   committano **prima** dell'upgrade come `chore(scraper)`, cosi' l'albero e' pulito quando
   parte il branch dell'SDK. (b -> eseguito come (a))

## Criteri di successo

1. `expo-doctor` 21/21 e `npx expo install --check` senza segnalazioni.
2. `npx expo export --platform web` verde.
3. Giro visivo: home con film del giorno, filtro con 8 cinema, località con 8 righe e 8
   marker senza pin rotti, dettaglio film con nomi leggibili.
4. Nessun `SDK 57` / `0.86` residuo nei documenti vivi (`grep`), escluso l'archivio
   (`docs/iss/**`, `docs/reviews/**`, presentazione, discorsi).
5. CI del branch verde (job *App*: export + doctor).
6. Riga di diario in coda a `docs/stato-e-diario.md`.

## Esclusioni

- Verifica su dispositivo iOS/Android reale: non disponibile in questo ambiente. La WebView
  nativa passa da export + allineamento versioni, non da una prova sul telefono. Va scritto
  nella riga di diario.
- `metro.config.js` e lo shim `codegenNativeComponent.web.js` non si toccano **se**
  l'export web resta verde; se si rompe, il blocco 7 diventa la loro correzione.
