#!/usr/bin/env bash
# Quan ly Typesense native binary (chay trong WSL).
# Usage: bash scripts/typesense.sh {start|stop|restart|status|health|logs}
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

# Load .env
set -a
# shellcheck disable=SC1091
source .env
set +a

BIN="$DIR/bin/typesense-server"
DATA_DIR="${TS_DATA_DIR:-$HOME/.typesense-legal/data}"
PORT="${TYPESENSE_PORT:-8108}"
PIDFILE="$DIR/typesense.pid"
LOG="$DIR/typesense.log"

mkdir -p "$DATA_DIR"

is_running() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

case "${1:-}" in
  start)
    if is_running; then
      echo "Typesense da chay (pid $(cat "$PIDFILE"))"; exit 0
    fi
    echo "Data dir: $DATA_DIR"
    nohup "$BIN" \
      --data-dir "$DATA_DIR" \
      --api-key "$TYPESENSE_API_KEY" \
      --listen-port "$PORT" \
      --enable-cors \
      > "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    echo "Started Typesense pid $(cat "$PIDFILE") tren port $PORT"
    ;;
  stop)
    if is_running; then
      kill "$(cat "$PIDFILE")" && rm -f "$PIDFILE"
      echo "Stopped."
    else
      echo "Khong chay."; rm -f "$PIDFILE" 2>/dev/null || true
    fi
    ;;
  restart)
    "$0" stop || true
    sleep 1
    "$0" start
    ;;
  status)
    if is_running; then echo "RUNNING pid $(cat "$PIDFILE")"; else echo "STOPPED"; fi
    ;;
  health)
    curl -s "http://${TYPESENSE_HOST:-localhost}:${PORT}/health"; echo
    ;;
  logs)
    tail -n "${2:-40}" "$LOG"
    ;;
  *)
    echo "Usage: bash scripts/typesense.sh {start|stop|restart|status|health|logs}"; exit 1
    ;;
esac
