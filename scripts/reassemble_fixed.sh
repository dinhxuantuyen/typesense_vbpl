#!/usr/bin/env bash
# Lap lai image voi entrypoint/healthcheck da fix. Parts da co san trong ~/legal-build-ctx.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."
CTX=~/legal-build-ctx

echo "=== [1/4] Cap nhat code + entrypoint moi vao context ==="
cp Dockerfile requirements.txt "$CTX/"
rm -rf "$CTX/legal_search" "$CTX/docker"
cp -r legal_search docker "$CTX/"
sed -i 's/\r$//' "$CTX/docker/entrypoint.sh"
ls "$CTX" | tr '\n' ' '; echo

echo "=== [2/4] Build SLIM (entrypoint moi) ==="
cd "$CTX"
sed '/^COPY data\/build\/ts-data\/ \/data\/$/d; /^COPY part[123]\/ \/data\/$/d' Dockerfile > Dockerfile.slim
docker build -t legal-mcp:slim -f Dockerfile.slim . 2>&1 | tail -2

echo "=== [3/4] Stage commits ==="
for N in 1 2 3; do
  docker rm -f lm-stage 2>/dev/null || true
  BASE=$([ "$N" = "1" ] && echo legal-mcp:slim || echo legal-mcp:stage$((N-1)))
  TARGET=$([ "$N" = "3" ] && echo legal-mcp:latest || echo legal-mcp:stage$N)
  echo "  stage$N: $BASE + part$N -> $TARGET"
  docker create --name lm-stage "$BASE" >/dev/null
  docker cp "part$N/." lm-stage:/data/
  docker commit lm-stage "$TARGET" >/dev/null
  docker rm -f lm-stage >/dev/null
  sleep 8
done
docker rmi legal-mcp:stage1 legal-mcp:stage2 2>/dev/null || true
docker inspect legal-mcp:latest --format 'EP={{.Config.Entrypoint}} HEALTH={{.Config.Healthcheck.Test}}'

echo "=== [4/4] TEST — theo doi bang docker logs, KHONG curl trong luc load ==="
docker rm -f legal-mcp-final 2>/dev/null || true
docker run -d --name legal-mcp-final -m 8g -p 8002:8000 -e EMBED_API_KEY=sk-1234 legal-mcp:latest >/dev/null
for i in $(seq 1 120); do
  sleep 5
  ST=$(docker ps -a --filter name=legal-mcp-final --format '{{.Status}}')
  LAST=$(docker logs legal-mcp-final 2>&1 | grep -E '^\[entrypoint\]' | tail -1)
  echo "  t=$((i*5))s | $ST | $LAST"
  echo "$ST" | grep -q Exited && { echo "=== CONTAINER CHET ==="; docker logs legal-mcp-final 2>&1 | tail -8; exit 1; }
  echo "$LAST" | grep -q 'MCP server' && { echo "=== TYPESENSE READY + MCP STARTED ==="; break; }
done
sleep 10
echo "--- xac nhan so document (an toan: da ready) ---"
docker exec legal-mcp-final curl -s -m 5 http://localhost:8108/collections/legal_articles \
  -H "X-TYPESENSE-API-KEY: poc_legal_search_2026" | grep -o '"num_documents":[0-9]*'
echo "=== HOAN TAT ==="
