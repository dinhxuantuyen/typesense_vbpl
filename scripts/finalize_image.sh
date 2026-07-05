#!/usr/bin/env bash
# Chay khi: (1) embed_offline da xong toan bo, (2) DNS docker da fix.
# Build index tu embedded.jsonl -> build image all-in-one -> (tuy chon) chay thu.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

EMBEDDED="${1:-data/build/embedded.jsonl}"
IMAGE="${IMAGE:-legal-mcp:latest}"

echo "==> [1/3] Build index Typesense tu $EMBEDDED (Phase B, khong goi proxy)..."
bash scripts/build_index.sh "$EMBEDDED"

echo "==> [2/3] docker build -t $IMAGE ..."
docker build -t "$IMAGE" .

echo "==> [3/3] Xong. Chay container:"
echo "    docker run -d --name legal-mcp -p 8000:8000 -e EMBED_API_KEY=sk-xxxx $IMAGE"
echo "    MCP endpoint: http://<host>:8000/mcp"
