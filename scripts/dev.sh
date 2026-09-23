#!/usr/bin/env bash
# Avvia tutto l'ambiente di sviluppo con un comando solo:
#   1. accende Docker Desktop se è spento e aspetta che sia pronto
#   2. avvia il backend (Docker)
#   3. rileva l'IP di rete del PC
#   4. avvia l'app Expo per web e telefono, con l'indirizzo giusto già configurato
#
# Uso:  make dev      (oppure: bash scripts/dev.sh)
# Stop: Ctrl+C
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPO_PORT="${EXPO_PORT:-8090}"
BACKEND_URL="http://localhost:8000"

info() { printf '\033[36m>\033[0m %s\n' "$1"; }
warn() { printf '\033[33m!\033[0m %s\n' "$1"; }
fail() { printf '\033[31mx\033[0m %s\n' "$1" >&2; exit 1; }

# ─── 1. Docker ────────────────────────────────────────────────────────────────
if ! docker info >/dev/null 2>&1; then
  info "Docker non e in esecuzione: lo avvio (ci mette un minuto)."
  case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*)
      DESKTOP="${LOCALAPPDATA:-}/Programs/DockerDesktop/Docker Desktop.exe"
      [ -f "$DESKTOP" ] || DESKTOP="/c/Program Files/Docker/Docker/Docker Desktop.exe"
      [ -f "$DESKTOP" ] || fail "Docker Desktop non trovato: avvialo a mano e riprova."
      cmd.exe /c start "" "$(cygpath -w "$DESKTOP")" >/dev/null 2>&1
      ;;
    Darwin*)
      open -a Docker || fail "Docker Desktop non installato."
      ;;
    *)
      fail "Docker non e attivo. Avvialo (sudo systemctl start docker) e riprova."
      ;;
  esac

  info "Aspetto che Docker sia pronto (fino a 3 minuti)..."
  for _ in $(seq 1 60); do
    docker info >/dev/null 2>&1 && break
    sleep 3
  done
  docker info >/dev/null 2>&1 ||
    fail "Docker non si e avviato. Apri Docker Desktop, guarda se chiede qualcosa (aggiornamenti, termini) e riprova."
fi

# ─── 2. Backend ───────────────────────────────────────────────────────────────
info "Avvio il backend..."
(cd "$REPO_DIR" && docker compose up -d backend >/dev/null)

# ─── 3. IP di rete (serve al telefono: dal telefono 'localhost' è il telefono) ─
detect_ip() {
  case "$(uname -s)" in
    MINGW* | MSYS* | CYGWIN*) ipconfig | grep -i "IPv4" | grep -v "127.0.0.1" | head -1 | awk '{print $NF}' ;;
    Darwin*) ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null ;;
    *) hostname -I 2>/dev/null | awk '{print $1}' ;;
  esac
}
IP="$(detect_ip || true)"
if [ -z "${IP:-}" ]; then
  warn "Non riesco a determinare l'IP di rete: il telefono non potra connettersi (il browser si)."
  IP="localhost"
fi

# ─── 4. Il backend risponde? ──────────────────────────────────────────────────
for _ in $(seq 1 30); do
  curl -s -o /dev/null "$BACKEND_URL/health" && break
  sleep 1
done
curl -s -o /dev/null "$BACKEND_URL/health" ||
  fail "Il backend non risponde su $BACKEND_URL. Guarda gli errori con: docker compose logs backend"

info "Backend pronto: $BACKEND_URL  (Swagger: $BACKEND_URL/docs)"
info "Dal telefono il backend e: http://$IP:8000"
info "Le tabelle sono gia popolate? Se l'app mostra 'nessun film': make seed"

# ─── 5. App ───────────────────────────────────────────────────────────────────
cd "$REPO_DIR/app"
if [ ! -d node_modules ]; then
  info "Prima volta: installo le dipendenze dell'app (2 minuti)..."
  npm install
fi

info "Avvio l'app Expo sulla porta $EXPO_PORT"
echo
echo "   Per vederla:  premi  w  ->  si apre nel browser"
echo "   Sul telefono:  Expo Go  ->  'Enter URL manually'  ->  exp://$IP:$EXPO_PORT"
echo "   (oppure inquadra il QR code che compare qui sotto)"
echo
echo "   Per fermare tutto: Ctrl+C"
echo

EXPO_PUBLIC_API_BASE="http://$IP:8000/api/v1" npx expo start --port "$EXPO_PORT"
