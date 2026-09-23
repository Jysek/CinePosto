# Sviluppo su Windows

> Verificato su `0c56a7e` (`2026-09-21`): intestazione aggiunta, contenuto non ancora ricontrollato.

Guida pratica per far girare CinePosto su Windows. Tutti i comandi qui sono stati eseguiti
e verificati su questo ambiente (Windows 11, Git Bash, Docker Desktop).

Il progetto si sviluppa su Windows e su macOS: il setup è **quasi identico**, cambiano solo
i percorsi e due dettagli di rete. La fonte di verità portabile resta la CI su Ubuntu
(`.github/workflows/ci.yml`).

---

## 1. Cosa serve installare (una volta sola)

| Strumento | Perché | Come |
|---|---|---|
| **Docker Desktop** | backend e scraper girano in container: **Python 3.12 non serve installarlo** | installato, va solo **avviato** |
| **Git** | ovvio | installato |
| **Node.js 20+** | solo per l'app Expo | installato (Node 24) |
| **make** *(opzionale)* | scorciatoie al posto dei comandi `docker compose` | `winget install --id ezwinports.make -e` |
| **GitHub CLI** *(opzionale)* | PR, release | `winget install --id GitHub.cli -e` |

**Python 3.12 non va installato su Windows**: vive dentro l'immagine Docker (`python:3.12-slim`).
Serve solo nel fallback "senza Docker" del §6, e in quel caso **deve** essere 3.12 (non 3.13/3.14:
`pydantic-core 2.27` non compila).

**Prima di ogni sessione di lavoro: avvia Docker Desktop** e aspetta che l'icona smetta di
girare. Se il daemon non è attivo, ogni comando `docker` fallisce con
`failed to connect to the docker API ... dockerDesktopLinuxEngine`.

---

## 2. Avvio quotidiano: un solo comando

Ogni volta che accendi il PC, per lavorare su CinePosto basta:

```bash
cd ~/dev/CinePosto
make dev
```

Su Windows puoi anche fare **doppio clic su `dev.cmd`** nella cartella del progetto: fa la stessa cosa
senza aprire il terminale.

`make dev` fa tutto da solo:

1. **accende Docker Desktop** se è spento e aspetta che sia pronto (un minuto circa);
2. avvia il **backend** e aspetta che risponda;
3. **ricava l'IP del PC** sulla rete locale;
4. avvia l'**app** con l'indirizzo del backend già configurato, sulla porta 8090;
5. stampa come vederla: premi `w` per il browser, oppure Expo Go con
   `exp://<IP>:8090` (oppure inquadra il QR).

Per fermare tutto: **Ctrl+C** nella finestra (o chiudila). I dati non si perdono: il database
resta su disco. Al riavvio successivo basta rifare `make dev`.

Se l'app dice *"nessun film in programmazione"*, il database è vuoto o vecchio:

```bash
make scrape   # scarica la programmazione aggiornata dai siti dei cinema
make seed     # la carica nel database
```

---

## 3. Primo avvio (solo la prima volta)

```bash
git clone https://github.com/Jysek/CinePosto.git ~/dev/CinePosto
cd ~/dev/CinePosto

docker compose up -d --build backend    # oppure: make up
docker compose run --rm backend python -m app.seed_from_json   # oppure: make seed
curl http://localhost:8000/health       # → {"status":"ok"}
```

- **Swagger UI**: http://localhost:8000/docs
- Il seed legge i JSON in `scraper/output/` e popola `backend/data/cineposto.db`.
  È idempotente: rilanciarlo non duplica nulla.

> I JSON committati sono un **dataset storico** (ultimo aggiornamento: 14 luglio 2026).
> Per questo `/api/v1/film/oggi` può rispondere `[]`: non ci sono spettacoli nella data odierna
> finché non si fa uno scraping vero (`docker compose run --rm scraper`).

---

## 4. Altri comandi utili

Con `make` (scorciatoia) o con il comando `docker compose` equivalente: sono la stessa cosa.

| Cosa | `make` | Comando per esteso |
|---|---|---|
| Avvia il backend | `make up` | `docker compose up -d --build backend` |
| Log del backend | `make logs` | `docker compose logs -f backend` |
| Stato container | `make ps` | `docker compose ps` |
| Test backend (31) | `make test` | `docker compose run --rm backend python -m pytest tests/ -q` |
| Test scraper (141) | `make test-scraper` | `docker compose run --rm scraper python -m pytest tests/ -q` |
| Lint (ruff check + format) | `make lint` | `ruff check` e `ruff format --check` su backend e scraper (4 comandi, vedi il target `lint` nel `Makefile`) |
| Messaggi di console ASCII | `make check-console` | controlla che `Makefile`, `dev.cmd` e `scripts/*.sh` stampino solo ASCII (vedi §9) |
| Seed del DB | `make seed` | `docker compose run --rm backend python -m app.seed_from_json` |
| Scraping **live** | `make scrape` | `docker compose run --rm scraper python -m scraper.main --once` |
| Shell nel container | `make shell` | `docker compose run --rm backend bash` |
| Ferma tutto | `make down` | `docker compose down` |
| Reset completo (cancella il DB) | `make clean` | `docker compose down -v --remove-orphans` + `rm backend/data/cineposto.db` |
| Aiuto | `make help` | — |

`docker compose run` avvia un container "usa e getta" per quel comando: non tocca il backend
che sta già girando, e non serve fermarlo per lanciare i test.

**Scraping: pochi giri, non venti al giorno.** I siti dei cinema non sono nostri. In sviluppo
usa i JSON già presenti come dati; lancia `make scrape` solo quando serve davvero un dataset
fresco (una o due volte a settimana). Rispetto di `robots.txt`, rate limiting e User-Agent
identificabile sono vincoli di progetto, non opzioni (vedi `NOTICE`).

---

## 5. App (Expo) su web e su iPhone

Con `make dev` l'app è già avviata con l'indirizzo giusto: salta questa sezione.
La trovi qui per il caso in cui voglia avviare l'app **da sola** (senza backend in Docker).

```bash
cd app
npm install

# Sostituisci <IP-LAN> con l'indirizzo del PC sulla rete locale:
#   PowerShell:  ipconfig | findstr IPv4
#   Git Bash:    ipconfig | grep IPv4
EXPO_PUBLIC_API_BASE="http://<IP-LAN>:8000/api/v1" npx expo start
```

- **Web**: apri http://localhost:8081 (o premi `w`).
- **iPhone**: apri **Expo Go** e scansiona il QR code.

> **Nota (SDK 57)** — Expo Go sugli store supporta **una sola versione dell'SDK**, che
> cambia a ogni release di Expo: non è una base stabile per un progetto che dura. Con il
> progetto su SDK 57, la strada consigliata per il nativo è un **development build**
> (`npx eas build --profile development --platform ios`), che si installa una volta sul
> telefono e non dipende da Expo Go. Su **Android**, `npx expo start` può installare da sé
> la versione di Expo Go corrispondente all'SDK in uso.

Non serve Android per sviluppare: l'app è React Native e gira anche su Android, ma non avendo
un device Android la verifica su quella piattaforma non è stata fatta.

### Se la porta 8081 è già occupata

Succede se hai un altro progetto Expo avviato (Metro tiene la 8081). Expo in modalità
non interattiva si ferma invece di chiedere. Usa un'altra porta **e aggiungi quell'origin
alla CORS del backend**, altrimenti il browser blocca le chiamate API:

```bash
# backend/.env
CORS_ORIGINS=["http://localhost:8081","http://localhost:8090",...]

# poi (il backend deve rileggere il .env: `restart` non basta)
docker compose up -d backend
expo start --web --port 8090
```

### Se il telefono non si connette

Quasi sempre è **rete o firewall**, non l'app. In ordine:

1. **Stessa Wi-Fi**: PC e iPhone devono essere sulla stessa rete, e il PC non deve essere
   connesso a una VPN.
2. **Profilo di rete "Privata"** su Windows: `Get-NetConnectionProfile` (PowerShell). Se dice
   `Public`, Windows blocca le connessioni in ingresso e Expo Go non raggiunge nulla:
   ```powershell
   Set-NetConnectionProfile -InterfaceAlias "Wi-Fi" -NetworkCategory Private
   ```
3. **Regola firewall per le porte 8000 (backend) e 8081/8090 (Metro)**. Su una rete
   **pubblica** (bar, università, hotspot) non conviene cambiare il profilo in Privato:
   meglio una regola limitata alla subnet locale. PowerShell **come amministratore**:
   ```powershell
   New-NetFirewallRule -DisplayName "CinePosto dev (LAN)" -Direction Inbound `
     -Protocol TCP -LocalPort 8000,8081,8090 -Action Allow -Profile Public -RemoteAddress LocalSubnet
   ```
   Se invece la rete è la tua di casa, il profilo Privato è la strada normale:
   ```powershell
   New-NetFirewallRule -DisplayName "CinePosto backend 8000" -Direction Inbound `
     -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
   ```
4. **IP cambiato**: il router assegna un IP nuovo → rileggi l'IP e riavvia `expo start`.

`localhost` **non** funziona dal telefono: `localhost`, sul telefono, è il telefono stesso.

---

## 6. Dove stanno i dati (e cosa non va mai committato)

| Percorso | Cos'è | Versionato? |
|---|---|---|
| `backend/data/cineposto.db` | DB SQLite di sviluppo (bind mount) | no |
| `scraper/output/*.json` | dataset (fixture di sviluppo, in prod è live) | **sì** |
| `scraper/output/cache/`, `history/` | cache per-cinema e snapshot giornalieri | no |
| `backend/.env` | configurazione locale (copia da `.env.example`) | no |
| `data/` | dati di **produzione** (DB + JSON live) | no |

Il file `.env` è opzionale in sviluppo: il backend ha default sensati. Se ti serve
personalizzarlo, `cp backend/.env.example backend/.env`. **Le variabili impostate in
`compose.yaml` hanno la precedenza** su quelle del file `.env`.

---

## 7. Fallback: senza Docker (venv nativo)

Serve **Python 3.12** installato (`winget install --id Python.Python.3.12 -e`, poi riapri il
terminale). Utile quando Docker non è disponibile; i comandi sono quelli di
[docs/development.md](development.md), tradotti per PowerShell.

```powershell
# Backend
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1        # Git Bash: source venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env
python -m app.seed_from_json
uvicorn app.main:app --reload --port 8000
```

```powershell
# Scraper
cd scraper
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m scraper.main --once
```

Differenze rispetto a macOS/Linux: `python3` → `py -3.12`, `source venv/bin/activate` →
`.\.venv\Scripts\Activate.ps1`, `ipconfig getifaddr en0` → `ipconfig | findstr IPv4`.

---

## 8. Produzione in locale

Verifica che la configurazione di produzione funzioni **prima** di toccare una VPS:

```bash
make prod-test      # Caddy con TLS self-signed su https://localhost:8443
curl -k https://localhost:8443/health
make prod-down
```

Cosa cambia in produzione (`compose.prod.yaml`): nessun codice bind-montato, backend non
pubblicato (l'unica porta esposta è Caddy su 80/443), backend come utente non privilegiato,
dati in `data/` fuori dal repo, `ADMIN_TOKEN` e `CORS_ORIGINS` obbligatori (il compose si
rifiuta di partire senza).

---

## 9. Problemi già incontrati (e soluzione)

| Sintomo | Causa | Soluzione |
|---|---|---|
| `failed to connect to the docker API` | Docker Desktop non avviato | avvia Docker Desktop, aspetta l'icona ferma |
| `port is already allocated` su 8000 | un backend già in ascolto | `make down`, oppure `netstat -ano \| findstr :8000` per trovare il processo |
| `/api/v1/film/oggi` → `[]` | dataset storico (luglio 2026) | `make scrape` + `make seed` |
| Il telefono non vede il backend | firewall / rete pubblica / IP cambiato | §4 |
| Fine riga strani nei diff | `core.autocrlf=true` su Windows | già gestito da `.gitattributes` (LF forzato) |
| Expo si ferma con "Port 8081 is being used" | un altro progetto Expo è avviato | `make dev` usa la 8090; per avviare a mano aggiungi `--port 8090` |
| Il browser blocca le chiamate API (CORS) | origin non in `CORS_ORIGINS` | aggiungila in `backend/.env` e `docker compose up -d backend` |
| Il terminale mostra `â€”` invece di `—` | la console non è UTF-8 (codepage 850) | i messaggi di `make` e degli script sono in ASCII proprio per questo: se vedi caratteri rotti esegui `chcp 65001` prima di `make`, o usa Windows Terminal. La regola è *ciò che `make` e gli script stampano deve essere ASCII; i file restano UTF-8*, e `make check-console` la fa rispettare |
| `python` apre il Microsoft Store | alias di Windows App Execution | usa `py -3.12` o il container |
