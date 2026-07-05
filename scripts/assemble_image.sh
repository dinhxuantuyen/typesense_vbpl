#!/usr/bin/env bash
# Chay SAU rebuild_index_snapshot.sh: tach part (KEM thu muc rong) -> build slim -> stage commit -> test.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

SRC=~/ts-build-data
CTX=~/legal-build-ctx

echo "=== [1/6] Lam moi context (code + entrypoint moi) ==="
rm -rf "$CTX/part1" "$CTX/part2" "$CTX/part3" "$CTX/data"
mkdir -p "$CTX/bin"
cp Dockerfile requirements.txt "$CTX/"
cp -r legal_search docker "$CTX/"        # docker/ chua entrypoint.sh MOI
cp bin/typesense-server "$CTX/bin/" 2>/dev/null || true
# CRLF -> LF cho entrypoint (viet tu Windows)
sed -i 's/\r$//' "$CTX/docker/entrypoint.sh"

echo "=== [2/6] Tach 3 part — KEM TOAN BO thu muc (ke ca rong) ==="
cd "$CTX"
for P in part1 part2 part3; do
  mkdir -p "$P"
  # tai tao day du cay thu muc trong ca 3 part (dam bao khong mat thu muc rong)
  (cd "$SRC" && find . -type d) | while read -r d; do
    mkdir -p "part1/$d" "part2/$d" "part3/$d"
  done
  break
done
i=0
(cd "$SRC" && find . -type f) | while read -r f; do
  dest="part$(( i % 3 + 1 ))/$f"
  ln "$SRC/$f" "$dest" 2>/dev/null || cp "$SRC/$f" "$dest"
  i=$((i+1))
done
du -sh part1 part2 part3

echo "=== [3/6] Build SLIM image ==="
sed '/^COPY data\/build\/ts-data\/ \/data\/$/d; /^COPY part[123]\/ \/data\/$/d' Dockerfile > Dockerfile.slim
docker build -t legal-mcp:slim -f Dockerfile.slim . 2>&1 | tail -2

echo "=== [4/6] Stage commits (moi layer <10GB) ==="
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

echo "=== [5/6] Kiem tra config + cau truc ==="
docker inspect legal-mcp:latest --format 'EP={{.Config.Entrypoint}}'
docker run --rm --entrypoint bash legal-mcp:latest -c 'ls /data; ls /data/state/snapshot | head -3'

echo "=== [6/6] TEST container (cho load toi da 5 phut) ==="
docker rm -f legal-mcp-final 2>/dev/null || true
docker run -d --name legal-mcp-final -p 8002:8000 -e EMBED_API_KEY=sk-1234 legal-mcp:latest >/dev/null
for i in $(seq 1 60); do
  sleep 5
  ND=$(docker exec legal-mcp-final curl -s -m 3 http://localhost:8108/collections/legal_articles -H "X-TYPESENSE-API-KEY: poc_legal_search_2026" 2>/dev/null | grep -o '"num_documents":[0-9]*' || true)
  ST=$(docker ps -a --filter name=legal-mcp-final --format '{{.Status}}')
  echo "  t=$((i*5))s status=$ST $ND"
  echo "$ST" | grep -q Exited && { echo "CONTAINER CHET:"; docker logs legal-mcp-final 2>&1 | tail -10; exit 1; }
  [ -n "$ND" ] && echo "$ND" | grep -q '37[0-9]\{4\}' && { echo "=== THANH CONG: $ND ==="; break; }
done
docker logs legal-mcp-final 2>&1 | tail -3
