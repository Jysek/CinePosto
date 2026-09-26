# Guida allo sviluppo

> Verificato su `056f04f` (`2026-09-26`): numeri dei test (181 scraper, 70 backend). Report del
> seed (`identity_conflicts`, `duplicate_titles`) e comandi confrontati col codice su `20ca1bb`.

> **Ambiente primario: Docker** (backend + scraper), uguale su Windows e macOS.
> Scorciatoie in `make help`; setup passo-passo su Windows in
> [development-windows.md](development-windows.md).
>
> Questa pagina descrive i comandi **nativi** (venv + npm), utili come fallback e su macOS.
>
> **Messaggi di console ASCII.** Ciò che `make` e gli script stampano resta ASCII: la console di
> Windows (CP850) non decodifica l'UTF-8 e i caratteri tipografici (`—`, `→`) uscirebbero corrotti
> (`â€”`). Il controllo è `make check-console`, che fallisce se una riga non-commento di `Makefile`,
> `dev.cmd` o `scripts/*.sh` contiene caratteri non ASCII. I file restano UTF-8: la regola riguarda
> solo ciò che finisce a schermo.

## Prerequisiti

- Python 3.12+
- Node.js 20+ (solo per app React Native)

---

## Scraper

### Setup

```bash
cd scraper
pip install -e ".[dev]"    # installa scraper + dipendenze dev (pytest, ruff, responses)
```

### Lint + test (comando canonico)

```bash
python3 -m ruff check scraper/ tests/ && python3 -m ruff format --check scraper/ tests/ && python3 -m pytest tests/ -q
```

### Test con coverage

```bash
python3 -m pytest tests/ --cov --cov-report=term-missing
```

### Esecuzione manuale

```bash
python3 -m scraper.main --once      # run singolo (è quello che usa systemd in produzione — L3)
python3 -m scraper.main --schedule  # SOLO DEV: loop APScheduler ogni 24h (richiede extra [dev])
python3 healthcheck.py              # ping alle 8 fonti
```

### Modifiche ai metadati o alle costanti cinema

Se cambi:
- `scraper/scraper/config.py` → `CINEMA_LOCATIONS` (nomi/indirizzi/coordinate)
- `scraper/scraper/metadata.py` → estrazione Wikidata (nuovi campi, nuove property)

...ricordati di **invalidare la cache Wikidata** prima di rilanciare, altrimenti riusa i vecchi risultati senza i nuovi campi:

```bash
rm scraper/.wikidata_cache.json
python3 -m scraper.main --once
```

Poi rigenera i JSON e reseed backend:

```bash
cd ../backend && source venv/bin/activate
rm cineposto.db
python -m app.seed_from_json
```

### Variabili d'ambiente

| Variabile | Default | Descrizione |
|---|---|---|
| `SCRAPER_TZ` | `Europe/Rome` | Fuso orario per calcolo "oggi" — importante se server è in UTC |
| `SCRAPER_LOG_LEVEL` | `INFO` | Livello di log (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CLOAKBROWSER_HEADLESS` | `true` | CloakBrowser in modalità headless |
| `CLOAKBROWSER_FINGERPRINT_SEED` | `42069` | Seed fingerprint anti-detection |

---

## Backend

### Setup

```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Seed del DB (una volta al primo avvio)

```bash
# Legge i JSON prodotti dallo scraper e popola cineposto.db
python -m app.seed_from_json
```

Da rilanciare **ogni volta che lo scraper aggiorna i JSON** (o via endpoint
admin `POST /api/v1/admin/reimport` col token in `X-Admin-Token`).

Il report stampato da `make seed` (identico al campo `imported` di `POST /api/v1/admin/reimport`)
è `{cinemas, films, showings, archived_films, reactivated_films, archived_showings,
reactivated_showings, skipped_cinemas, identity_conflicts, duplicate_titles}`. Le ultime due chiavi
sono coppie `"A:B"` pronte per `python -m app.maintenance.dedup_films --merge A:B` (conflitti di
identità fra due righe e titoli duplicati con anno NULL): il seed **segnala**, non fonde mai da
solo.

### Manutenzione: fondere i film duplicati

Quando le run accumulate lasciano due righe per lo stesso film (titolo scritto diversamente,
anno NULL), si usa lo script di manutenzione — **dry-run di default**, `--apply` per scrivere,
`--merge A:B` per una fusione approvata a mano:

```bash
docker compose run --rm backend python -m app.maintenance.dedup_films               # DRY-RUN + report
docker compose run --rm backend python -m app.maintenance.dedup_films --apply       # applica
docker compose run --rm backend python -m app.maintenance.dedup_films --merge 40:52 # fusione esplicita
```

Si usa **dopo** aver notato doppioni nell'app o nel DB, mai a orari fissi: le regole di fusione,
il report e le garanzie (una transazione, rollback, idempotenza) sono in
[backend/architecture.md](backend/architecture.md) § Manutenzione.

### Avvio server

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`.

### Test

```bash
python -m pytest tests/ -q       # 70 test (~0.2s)
python -m pytest tests/ -v       # verbose
```

Setup dei test:
- `conftest.py` — SQLite in-memory + `StaticPool` + override di `get_db`
- `test_config.py` — 5 test sulla configurazione (token admin, path, CORS)
- `test_repositories.py` — 21 unit test sui repository (normalizzazione titoli, upsert, search)
- `test_routers.py` — 12 end-to-end via TestClient FastAPI
- `test_maintenance_dedup.py` — 10 test sullo script di fusione dei film duplicati
- `test_seed_archive.py` — 8 test sull'archiviazione dei residui del seed (soft delete)
- `test_seed_identity.py` — 8 test sulla guardia di identità del seed (un film = una riga: riuso via `wikidata_id`, conflitti segnalati)
- `test_maintenance_migrate_removed_at.py` — 4 test sulla migrazione idempotente delle colonne `removed_at`

### Variabili d'ambiente (`.env`)

| Variabile | Default | Descrizione |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./cineposto.db` | Path DB. In dev SQLite locale, in prod idem (D4) |
| `SCRAPER_OUTPUT_DIR` | `../scraper/output` | Cartella JSON scraper (risolto a path assoluto) |
| `CORS_ORIGINS` | *(dev defaults)* | JSON array; se vuoto usa `localhost:8081/19006/3000` |
| `ENV` | `development` | `development` → SQL echo + `create_all` in lifespan |
| `LOG_LEVEL` | `INFO` | |
| `SEED_ARCHIVE_ENABLED` | `true` | Il seed archivia i residui non più nei JSON (`removed_at`), mai cancellati. `false` = solo upsert |
| `SEED_ARCHIVE_MIN_RATIO` | `0.5` | Guardia anti-fonte-rotta: sotto questo ratio importati/già nel DB l'archiviazione per quel cinema si salta |
| `ADMIN_TOKEN` | *(auto-generato)* | Se vuoto o `"change-me-before-deploy"`, il backend genera un token random e lo stampa una volta al boot |

---

## App (React Native)

App integrata e collegata al backend (React Navigation, **Expo SDK 57**). **NON usare
`create-expo-app`** — il progetto è già inizializzato e per il nativo serve un
**development build** (`expo prebuild` + EAS), non Expo Go.

```bash
cd app
npm install
# IP LAN del Mac (macOS): ipconfig getifaddr en0
EXPO_PUBLIC_API_BASE="http://<IP-LAN>:8000/api/v1" npx expo start
```

- **Web**: apri `http://localhost:8081` (o premi `w`).
- **Telefono**: Expo Go → scansiona il QR (telefono e backend sulla stessa Wi-Fi).
- **Build web statica**: `npx expo export --platform web` → `dist/`.

Il backend dev'essere in esecuzione su `0.0.0.0:8000` con il DB seedato. Setup
completo in [docs/app/overview.md](app/overview.md).

---

## Deploy scraper su Linux

```bash
./scraper/deploy/setup.sh   # installa systemd timer + service oneshot + logrotate

sudo systemctl list-timers cineposto-scraper.timer       # prossima esecuzione schedulata
sudo systemctl status cineposto-scraper.service          # ultima run
sudo systemctl start cineposto-scraper.service           # forza run manuale subito
sudo journalctl -u cineposto-scraper.service -f --since "1 hour ago"
```
