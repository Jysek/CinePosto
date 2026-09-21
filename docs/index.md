# Documentazione CinePosto

Aggregatore della programmazione dei cinema dell'Umbria: uno scraper Python raccoglie i palinsesti,
un backend FastAPI li serve via REST, un'app React Native (Expo) li mostra su web, iOS e Android.
Nessuna registrazione utente.

> Questa cartella racconta **cosa il progetto è oggi**, non la sua storia. Se un capitolo
> contraddice il codice, vince il codice e il capitolo si corregge. Ogni documento vivo dichiara in
> testa su quale commit è stato verificato; gli archivi sono esclusi da questa regola.

## Da dove cominciare

| Se sei… | Leggi in quest'ordine |
|---|---|
| L'agente che deve fare una modifica | `stato-e-diario.md` (dove siamo) → `problemi-aperti.md` (cosa è rotto) → il capitolo dell'area che tocchi |
| Nuovo nel progetto | `panoramica.md` → `development-windows.md` (oppure `development.md`) |
| Devi lavorare sullo scraper | `scraper/architecture.md` → `scraper/copertura.md` → `scraper/connettori/README.md` |
| Devi lavorare sul backend | `backend/architecture.md` → `backend/schema-mapping.md` → `backend/api.md` |
| Devi lavorare sull'app | `app/overview.md` |
| Devi mettere in produzione | `deploy.md` |

## Indice

| File | Cosa trovi | Stato |
|---|---|---|
| `stato-e-diario.md` | Dove siamo oggi e la storia delle sessioni | si aggiorna a ogni sessione |
| `problemi-aperti.md` | Cosa non funziona oggi, con la prova | si accorcia quando si risolve |
| `panoramica.md` | Il sistema da cima a fondo: flusso dei dati, componenti, decisioni | completo |
| `development.md` | Setup nativo (venv + npm), test, lint, variabili d'ambiente | completo |
| `development-windows.md` | Setup su Windows con Docker, app sul telefono, firewall | completo |
| `deploy.md` | Produzione: VPS, Caddy, scraping notturno, backup | completo |
| `scraper/architecture.md` | Connettori, normalizzazione, Wikidata, delta, deploy systemd | completo |
| `scraper/copertura.md` | Registro delle sale dell'Umbria: cosa è coperto e cosa no | si aggiorna a ogni sala |
| `scraper/connettori/README.md` | Come si scrive un connettore e quali esistono | completo |
| `backend/architecture.md` | Layering, modelli, endpoint | completo |
| `backend/schema-mapping.md` | Come ogni campo JSON diventa colonna (autorevole per il seed) | completo |
| `backend/api.md` | Contratto API completo | completo |
| `app/overview.md` | Stack, schermate, client API, avvio | completo |
| `app/integrazione-e-fix.md` | Storia dell'integrazione dell'app nel monorepo | da valutare (Fase 3) |
| `iss/*`, `presentazione-14-luglio.*`, `esposizione-discorsi.*` | Materiale d'esame del 14 luglio 2026 | archivio, non si aggiorna |

## Archivio: materiale d'esame (14 luglio 2026)

Questi documenti raccontano il progetto **così com'era all'esposizione**. Restano come archivio
storico e **non si aggiornano**: `iss/analisi-requisiti.md`, `iss/sprint-plan.md`,
`iss/progettazione-uml.md`, `presentazione-14-luglio.md` (+ `.pdf`, `.pptx`),
`esposizione-discorsi.md` (+ `.pdf`).

## Convenzioni di questa documentazione

1. **Ingresso unico**: si arriva da questo indice.
2. **Intestazione di verifica** in ogni documento vivo: `> Verificato su <commit> (<data>).`
3. **Diagrammi in Mermaid**, così restano testo modificabile.
4. **Prosa** in italiano, frasi dirette, niente riempitivi. Si spiega il *perché* dove conta.
5. **Niente cronologia dentro i capitoli**: la storia sta solo in `stato-e-diario.md`.
6. **Riferimenti al codice** come `scraper/scraper/config.py`; il numero di riga solo dove serve
   come prova (problemi aperti).
