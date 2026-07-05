#!/usr/bin/env bash
# Rebuild index tren ext4 + TRIGGER SNAPSHOT (fix loi "Snapshot does not exist -> wipe db").
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
set -a; source .env; set +a

EMB=~/embedded.jsonl
DATA=~/ts-build-data
PORT=8109

echo "=== [1/5] Copy embedded.jsonl C: -> ext4 ==="
if [ ! -f "$EMB" ]; then
  time cp /mnt/c/legal_backup/embedded.jsonl "$EMB"
fi
ls -lh "$EMB"

echo "=== [2/5] Khoi dong Typesense tam (fresh) ==="
rm -rf "$DATA"; mkdir -p "$DATA"
./bin/typesense-server --data-dir "$DATA" --api-key "$TYPESENSE_API_KEY" \
  --api-port $PORT --peering-port $((PORT+1)) > ~/ts-build.log 2>&1 &
TS_PID=$!
trap 'kill $TS_PID 2>/dev/null || true' EXIT
for i in $(seq 1 60); do
  curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1 && break; sleep 1
done
echo "Typesense tam OK (pid $TS_PID)"

echo "=== [3/5] Import 378k documents (~45 phut) ==="
TYPESENSE_PORT=$PORT python3 -m legal_search.import_embedded --input "$EMB" --recreate --batch 2000 2>&1 | tail -3

echo "=== [4/5] TRIGGER SNAPSHOT (quan trong!) ==="
mkdir -p ~/ts-snapshot-tmp
curl -s -X POST "http://localhost:$PORT/operations/snapshot?snapshot_path=$HOME/ts-snapshot-tmp" \
  -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"; echo
sleep 20   # cho snapshot ghi xong vao state/snapshot

echo "=== [5/5] Dung server SACH (SIGTERM + doi thoat) ==="
kill -TERM $TS_PID
for i in $(seq 1 60); do kill -0 $TS_PID 2>/dev/null || break; sleep 1; done
trap - EXIT
echo "--- kiem tra snapshot trong state ---"
find "$DATA/state/snapshot" -maxdepth 1 | head -5
du -sh "$DATA"
echo "XONG. Data dir: $DATA"
