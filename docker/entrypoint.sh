#!/usr/bin/env bash
# Entrypoint all-in-one: chay Typesense (index baked) + MCP server, trap tin hieu de tat sach.
set -e

: "${TYPESENSE_API_KEY:=poc_legal_search_2026}"

echo "[entrypoint] Khoi dong Typesense (data /data)..."
typesense-server --data-dir /data --api-key "$TYPESENSE_API_KEY" --listen-port 8108 &
TS_PID=$!

echo "[entrypoint] Cho Typesense health..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:8108/health >/dev/null 2>&1; then
    echo "[entrypoint] Typesense OK"; break
  fi
  sleep 1
done

echo "[entrypoint] Khoi dong MCP server tren :${MCP_PORT:-8000}..."
python -m legal_search.mcp_server &
MCP_PID=$!

term() { echo "[entrypoint] Nhan tin hieu dung, tat cac tien trinh..."; kill -TERM "$MCP_PID" "$TS_PID" 2>/dev/null || true; }
trap term TERM INT

# Neu 1 trong 2 tien trinh thoat -> dung ca container
wait -n "$TS_PID" "$MCP_PID"
term
wait || true
