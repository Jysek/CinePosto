#!/usr/bin/env bash
# Harness di verifica dell'app web: costruisce l'export statico, lo serve in
# locale e ricorda la checklist di accettazione. È pensato per essere eseguito
# identico dopo ogni passo dell'upgrade di Expo SDK, così un difetto introdotto
# dalla nuova SDK si distingue da un problema preesistente.
#
# Uso:   bash scripts/check-app-web.sh [porta]     (default 3000)
# Stop:  Ctrl+C
#
# Prerequisiti:
#   - backend su e popolato:            make up && make seed
#   - l'origin http://localhost:<porta> presente in CORS_ORIGINS (backend/.env)
#   - Node installato (per l'export e per il server statico)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${1:-${PORT:-3000}}"
API_BASE="${EXPO_PUBLIC_API_BASE:-http://localhost:8000/api/v1}"
OUT_DIR="${OUT_DIR:-$REPO_DIR/app/dist}"
HEALTH_URL="${API_BASE%/api/v1}/health"

info() { printf '\033[36m▸\033[0m %s\n' "$1"; }
warn() { printf '\033[33m!\033[0m %s\n' "$1"; }
fail() { printf '\033[31m✗\033[0m %s\n' "$1" >&2; exit 1; }

command -v node >/dev/null 2>&1 || fail "Node non trovato nel PATH."

# Il backend è il prerequisito di ogni controllo: senza dati la checklist mente.
if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
  info "Backend raggiungibile su $HEALTH_URL"
else
  fail "Backend non raggiungibile su $HEALTH_URL — avvia: make up && make seed"
fi

if curl -sf -o /dev/null "$API_BASE/cinema"; then
  CINEMAS=$(curl -s "$API_BASE/cinema" | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>console.log(JSON.parse(d).length))')
  info "L'API espone $CINEMAS cinema"
else
  warn "GET $API_BASE/cinema non risponde: il seed è stato eseguito?"
fi

info "Export web in $OUT_DIR (API_BASE=$API_BASE)..."
rm -rf "$OUT_DIR"
(cd "$REPO_DIR/app" && EXPO_PUBLIC_API_BASE="$API_BASE" npx expo export --platform web --output-dir "$OUT_DIR")

cat <<CHECKLIST

────────────────────────────────────────────────────────────────────────────
Checklist di accettazione — da ripassare nel browser su
http://localhost:$PORT   (oppure con Playwright)
────────────────────────────────────────────────────────────────────────────
  [ ] Home "Film": la lista si carica, nessuno stato di errore
  [ ] Filtro: elenca 8 cinema; selezionandone uno i film cambiano
  [ ] Località: 8 righe e 8 marker sulla mappa, nessun pin rotto
  [ ] Dettaglio film: nomi leggibili (non slug), ordine alfabetico,
      badge/logo coerenti
  [ ] Aspetto invariato: stessi stili e colori di prima dell'upgrade
────────────────────────────────────────────────────────────────────────────

CHECKLIST

exec node "$REPO_DIR/scripts/serve-web.mjs" "$OUT_DIR" "$PORT"
