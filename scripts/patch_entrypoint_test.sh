#!/usr/bin/env bash
# Va entrypoint moi vao image (1 layer nho) + test voi --ulimit nofile.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

TMP=/tmp/entrypoint.sh
cp docker/entrypoint.sh "$TMP"
sed -i 's/\r$//' "$TMP"

echo "=== [1/2] Va entrypoint vao image ==="
docker rm -f lm-patch 2>/dev/null || true
docker create --name lm-patch legal-mcp:latest >/dev/null
docker cp "$TMP" lm-patch:/app/entrypoint.sh
docker commit lm-patch legal-mcp:latest >/dev/null
docker rm lm-patch >/dev/null
echo "patched."

echo "=== [2/2] TEST voi --ulimit nofile=65535 ==="
docker rm -f legal-mcp-final 2>/dev/null || true
docker run -d --name legal-mcp-final -m 8g --ulimit nofile=65535:65535 \
  -p 8002:8000 -e EMBED_API_KEY=sk-1234 legal-mcp:latest >/dev/null
for i in $(seq 1 150); do
  sleep 5
  ST=$(docker ps -a --filter name=legal-mcp-final --format '{{.Status}}')
  LAST=$(docker logs legal-mcp-final 2>&1 | grep -E '^\[entrypoint\]' | tail -1)
  echo "  t=$((i*5))s | $ST | $LAST"
  echo "$ST" | grep -q Exited && { echo "=== CONTAINER CHET ==="; docker logs legal-mcp-final 2>&1 | tail -8; exit 1; }
  echo "$LAST" | grep -q 'MCP server' && { echo "=== READY ==="; break; }
done
sleep 8
echo "--- so document ---"
docker exec legal-mcp-final curl -s -m 5 http://localhost:8108/collections/legal_articles \
  -H "X-TYPESENSE-API-KEY: poc_legal_search_2026" | grep -o '"num_documents":[0-9]*'
echo "=== HOAN TAT ==="
