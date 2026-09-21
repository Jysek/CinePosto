# Deploy

> Verificato su `0c56a7e` (`2026-09-21`): intestazione aggiunta, contenuto non ancora ricontrollato.

Come CinePosto va in produzione. La configurazione **è già nel repo e verificata in locale**
(`make prod-test`): sulla VPS resta da eseguire, non da progettare.

> **Stato**: procedura pronta, non ancora eseguita. La VPS Oracle (Always Free) va ancora creata.

## Architettura

```
                    ┌────────────────────────── VPS (Oracle Always Free, Arm) ─────────────────────────┐
   internet ──443──▶│  caddy (HTTPS, Let's Encrypt)  ──▶  backend (uvicorn, utente non privilegiato)     │
                    │                                        │                                      │
                    │                                        ├── /data/cineposto.db   (SQLite)       │
                    │                                        └── /scraper/output/*.json (sola lett.) │
                    │  systemd timer 03:00 ──▶ scraper (one-shot) ──▶ ./data/output/*.json             │
                    └───────────────────────────────────────────────────────────────────────────────────┘
```

- Solo Caddy è raggiungibile da fuori (porte 80/443). Il backend **non** ha porte pubblicate.
- I dati stanno in `./data` (fuori dal repo): `data/db` (SQLite) e `data/output` (JSON dello scraper).
- `git pull` non tocca mai i dati, perché non c'è codice bind-montato in produzione.

## 1. Creare la VPS

Oracle Cloud → **Always Free**: `VM.Standard.A1.Flex`, **2 OCPU / 12 GB**, immagine
**Ubuntu 24.04 (Arm)**, nella *home region*. Se compare "out of host capacity", riprova in
un'altra availability domain o più tardi.

Due accorgimenti:

- **Passa a Pay As You Go** (resti a 0 € dentro i limiti Always Free): le istanze Always Free
  vengono **reclamate** se per 7 giorni CPU p95 < 20%, rete < 20% e memoria < 20% — un'API a
  basso traffico è esattamente quel profilo.
- Apri le porte **80 e 443** nella security list del VCN (di default è aperta solo la 22).

## 2. Preparare la macchina (una volta)

```bash
ssh ubuntu@<ip>
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu && exit   # rientra per avere il gruppo docker
git clone https://github.com/Jysek/CinePosto.git /opt/cineposto   # o git@github.com:...
cd /opt/cineposto
```

## 3. Configurare i segreti

Creare `/opt/cineposto/.env.prod` (non versionato):

```bash
DOMAIN=cineposto.example.org
CORS_ORIGINS=["https://cineposto.example.org"]
ADMIN_TOKEN=<genera con: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
```

`compose.prod.yaml` **si rifiuta di partire** senza `ADMIN_TOKEN` e `CORS_ORIGINS`: è voluto.

Il DNS del dominio deve puntare all'IP della VPS **prima** del primo avvio, altrimenti Caddy
non riesce a ottenere il certificato Let's Encrypt (per una prova senza dominio si può usare
`DOMAIN=<ip>.sslip.io`).

## 4. Primo avvio

```bash
cd /opt/cineposto
mkdir -p data/output data/db

docker compose -f compose.yaml -f compose.prod.yaml --env-file .env.prod up -d --build
docker compose -f compose.yaml -f compose.prod.yaml --env-file .env.prod run --rm scraper   # primo scrape reale
docker compose -f compose.yaml -f compose.prod.yaml --env-file .env.prod run --rm backend python -m app.seed_from_json

curl https://cineposto.example.org/health     # → {"status":"ok"}
```

I target equivalenti del Makefile usano già `--env-file .env.prod`:
`make prod-up`, `make prod-scrape`, `make prod-seed`.

## 5. Scraping notturno (systemd timer)

I file in `scraper/deploy/` sono la versione "nativa" (Python sulla macchina). In Docker il
timer lancia il container:

```ini
# /etc/systemd/system/cineposto-scraper.service
[Unit]
Description=CinePosto — scraping notturno
After=docker.service network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/cineposto
ExecStart=/usr/bin/docker compose -f compose.yaml -f compose.prod.yaml --env-file .env.prod run --rm scraper
ExecStartPost=/usr/bin/docker compose -f compose.yaml -f compose.prod.yaml --env-file .env.prod run --rm backend python -m app.seed_from_json
```

```ini
# /etc/systemd/system/cineposto-scraper.timer
[Unit]
Description=CinePosto — trigger giornaliero alle 03:00

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
RandomizedDelaySec=10min

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now cineposto-scraper.timer
systemctl list-timers cineposto-scraper.timer
```

## 6. Backup

Tutto ciò che conta sta in `./data` (DB + JSON):

```bash
tar czf ~/cineposto-$(date +%F).tar.gz -C /opt/cineposto data
```

Backup automatico giornaliero con timer systemd, oppure `rclone` verso l'Object Storage
Always Free di Oracle (10 GB). Ripristino: scompattare `data/` e riavviare lo stack.

## 7. Aggiornare

```bash
cd /opt/cineposto
git pull
docker compose -f compose.yaml -f compose.prod.yaml --env-file .env.prod up -d --build
```

Nessun bind mount di codice: il riavvio usa la nuova immagine, i dati restano.

## Verifica in locale prima di toccare la VPS

```bash
make prod-test        # Caddy con TLS self-signed su https://localhost:8443
curl -k https://localhost:8443/health
make prod-down
```

Questo controlla la stessa configurazione (volumi, Caddy, variabili obbligatorie) senza
rischiare sulla macchina di produzione. In CI il file viene validato a ogni push con
`docker compose ... config --quiet`.
