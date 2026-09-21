# CinePosto — Stato attuale e diario

> Verificato su `0c56a7e` (`2026-09-21`).

**Come si usa questo file.** La sezione «Stato attuale» è una fotografia di oggi e si **riscrive**
quando cambia. La sezione «Diario» è **append-only**: si aggiunge in coda, non si riscrive mai il
passato e non si cancellano le righe precedenti.

## Stato attuale

**Cosa funziona end-to-end**: lo scraping delle sale coperte, il backend FastAPI e l'app Expo su
web, iOS e Android dalla stessa codebase. La CI testa backend, scraper e export web a ogni push.

| Area | Stato | Dove |
|---|---|---|
| Scraper | 8 connettori attivi | `scraper/copertura.md` |
| Backend | 11 endpoint REST, 31 test | `backend/api.md` |
| App | web + iOS + Android, dati dall'API | `app/overview.md` |
| Deploy | procedura pronta e verificata in locale, non ancora eseguita sulla VPS | `deploy.md` |

**In corso / prossimo passo**: estensione della copertura a tutte le sale dell'Umbria (8 connettori
su 30 sale note, 11 con sito noto e tecnica da analizzare — vedi `scraper/copertura.md`). Restano
aperti l'avviso "dati non aggiornati" nell'app e il primo deploy sulla VPS (`problemi-aperti.md`).

**Fuori scope per scelta**: account utente, acquisto biglietti in-app, notifiche push.

## Diario

Una riga per sessione, in coda. Formato: `- **<data>** — cosa è stato fatto, decisioni, note.`

- **2026-09-21** — creata la struttura di memoria della documentazione: questo diario, il registro
  `problemi-aperti.md`, l'indice `docs/index.md` rinnovato e l'intestazione di verifica su tutti i
  documenti vivi. Nessun cambiamento al codice.
