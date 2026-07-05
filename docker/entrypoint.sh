#!/usr/bin/env bash
# Entrypoint all-in-one: Typesense (index baked) + MCP server. Giam sat 2 tien trinh bang vong lap.

: "${TYPESENSE_API_KEY:=poc_legal_search_2026}"

echo "[entrypoint] Khoi dong Typesense (data /data)..."
typesense-server --data-dir /data --api-key "$TYPESENSE_API_KEY" --listen-port 8108 &
TS_PID=$!

echo "[entrypoint] Cho Typesense health (toi da 300s — index lon can thoi gian load)..."
HEALTHY=0
for i in $(seq 1 300); do
  if ! kill -0 "$TS_PID" 2>/dev/null; then
    echo "[entrypoint] LOI: Typesense da thoat khi dang khoi dong."; exit 1
  fi
  if curl -sf http://localhost:8108/health 2>/dev/null | grep -q '"ok":true'; then
    HEALTHY=1; echo "[entrypoint] Typesense OK (sau ${i}s)"; break
  fi
  sleep 1
done
if [ "$HEALTHY" -ne 1 ]; then
  echo "[entrypoint] LOI: Typesense khong healthy sau 300s."; kill "$TS_PID" 2>/dev/null; exit 1
fi

echo "[entrypoint] Khoi dong MCP server tren :${MCP_PORT:-8000}..."
python -m legal_search.mcp_server &
MCP_PID=$!

term() {
  echo "[entrypoint] Nhan tin hieu dung, tat cac tien trinh..."
  kill -TERM "$MCP_PID" "$TS_PID" 2>/dev/null
  wait "$MCP_PID" "$TS_PID" 2>/dev/null
  exit 0
}
trap term TERM INT

# Giam sat: neu 1 trong 2 tien trinh chet -> dung container (de docker restart policy xu ly)
while kill -0 "$TS_PID" 2>/dev/null && kill -0 "$MCP_PID" 2>/dev/null; do
  sleep 5
done
echo "[entrypoint] Mot tien trinh da thoat — dung container."
kill -TERM "$MCP_PID" "$TS_PID" 2>/dev/null
exit 1
