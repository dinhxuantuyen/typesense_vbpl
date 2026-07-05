#!/usr/bin/env bash
# Trien khai local theo dung flow DEPLOY.md: deploy -> import full -> snapshot.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "=== [1/4] Don cho: dung host-typesense/MCP cu neu con, go container cu ==="
for p in $(pgrep -f '[t]ypesense-server --data-dir /home'); do kill "$p" 2>/dev/null || true; done
for p in $(pgrep -f '[l]egal_search.mcp_server'); do kill "$p" 2>/dev/null || true; done
docker rm -f legal-mcp 2>/dev/null || true
sleep 2

echo "=== [2/4] Deploy container legal-mcp (volume moi legal-data) ==="
docker volume rm legal-data 2>/dev/null || true
docker run -d --name legal-mcp \
  --restart unless-stopped \
  -p 8000:8000 -p 8108:8108 \
  -v legal-data:/data \
  -v /mnt/c/legal_backup:/import:ro \
  --ulimit nofile=65535:65535 \
  -m 8g \
  -e TYPESENSE_API_KEY='poc_legal_search_2026' \
  -e EMBED_API_KEY='sk-1234' \
  legal-mcp:slim >/dev/null
echo "cho MCP len..."
for i in $(seq 1 30); do
  sleep 2
  docker logs legal-mcp 2>&1 | grep -q 'Uvicorn running' && { echo "services OK (sau $((i*2))s)"; break; }
done
docker ps --filter name=legal-mcp --format '{{.Status}}'

echo "=== [3/4] Bat dashboard ==="
docker start typesense-dashboard 2>/dev/null || \
  docker run -d --name typesense-dashboard --restart unless-stopped -p 8888:80 bfritscher/typesense-dashboard:latest >/dev/null
echo "dashboard: http://localhost:8888"

echo "=== [4/4] IMPORT FULL 378k (~30-50 phut) ==="
docker exec legal-mcp python -m legal_search.import_embedded \
  --input /import/embedded.jsonl --recreate --batch 2000 2>&1 | tail -4

echo "=== SNAPSHOT ==="
docker exec legal-mcp bash -c 'curl -s -X POST "http://localhost:8108/operations/snapshot?snapshot_path=/data/backup" -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"'
echo
echo "=== DEPLOY LOCAL HOAN TAT ==="
