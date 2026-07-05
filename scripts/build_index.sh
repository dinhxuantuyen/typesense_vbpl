#!/usr/bin/env bash
# Phase B (host-side): tao san data dir Typesense tu embedded.jsonl -> data/build/ts-data
# de Dockerfile COPY vao image. KHONG goi proxy.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

set -a; source .env; set +a

BUILD_DATA="data/build/ts-data"
BUILD_PORT="${BUILD_PORT:-8109}"
EMBEDDED="${1:-data/build/embedded.jsonl}"

rm -rf "$BUILD_DATA"
mkdir -p "$BUILD_DATA"

echo "[build_index] Khoi dong Typesense tam tren port $BUILD_PORT (peering $((BUILD_PORT+1)))..."
./bin/typesense-server --data-dir "$BUILD_DATA" --api-key "$TYPESENSE_API_KEY" \
  --api-port "$BUILD_PORT" --peering-port "$((BUILD_PORT+1))" > data/build/ts-build.log 2>&1 &
TS_PID=$!
trap 'kill $TS_PID 2>/dev/null || true' EXIT

for i in $(seq 1 60); do
  if curl -sf "http://localhost:$BUILD_PORT/health" >/dev/null 2>&1; then echo "[build_index] Typesense OK"; break; fi
  sleep 1
done

echo "[build_index] Import $EMBEDDED ..."
TYPESENSE_PORT="$BUILD_PORT" python3 -m legal_search.import_embedded --input "$EMBEDDED" --recreate --batch 2000

echo "[build_index] Dung Typesense tam..."
kill "$TS_PID" 2>/dev/null || true
wait "$TS_PID" 2>/dev/null || true
trap - EXIT

echo "[build_index] XONG. Data dir san sang: $BUILD_DATA"
du -sh "$BUILD_DATA"
