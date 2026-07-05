#!/usr/bin/env bash
# Entrypoint all-in-one: Typesense (index baked) + MCP server.
# QUAN TRONG: Typesense 29 co the segfault neu nhan HTTP request trong luc load snapshot
# -> cho readiness bang cach DOC LOG, tuyet doi khong curl truoc khi san sang.

: "${TYPESENSE_API_KEY:=poc_legal_search_2026}"
ulimit -c 0                          # chan core dump (index lon -> core 16GB co the lam treo he thong)
ulimit -n 65535 2>/dev/null || true  # raft log co hang nghin segment file -> can nofile cao
echo "[entrypoint] nofile limit: $(ulimit -n)"

TSLOG=/tmp/typesense.log
echo "[entrypoint] Khoi dong Typesense (data /data)..."
typesense-server --data-dir /data --api-key "$TYPESENSE_API_KEY" --api-port 8108 > "$TSLOG" 2>&1 &
TS_PID=$!

echo "[entrypoint] Cho Typesense load xong (doc log, KHONG goi HTTP)..."
READY=0
for i in $(seq 1 600); do
  if ! kill -0 "$TS_PID" 2>/dev/null; then
    echo "[entrypoint] LOI: Typesense thoat khi khoi dong. Log cuoi:"; tail -5 "$TSLOG"; exit 1
  fi
  if grep -qE 'become leader of group|Peer refresh succeeded' "$TSLOG" 2>/dev/null; then
    READY=1; echo "[entrypoint] Typesense san sang (sau ${i}s)"; break
  fi
  sleep 1
done
if [ "$READY" -ne 1 ]; then
  echo "[entrypoint] LOI: Typesense chua san sang sau 600s."; tail -5 "$TSLOG"; kill "$TS_PID" 2>/dev/null; exit 1
fi
# xac nhan lan cuoi bang health (an toan vi da san sang)
curl -sf http://localhost:8108/health >/dev/null 2>&1 && echo "[entrypoint] Health OK"

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

while kill -0 "$TS_PID" 2>/dev/null && kill -0 "$MCP_PID" 2>/dev/null; do
  sleep 5
done
echo "[entrypoint] Mot tien trinh da thoat — dung container."
kill -TERM "$MCP_PID" "$TS_PID" 2>/dev/null
exit 1
