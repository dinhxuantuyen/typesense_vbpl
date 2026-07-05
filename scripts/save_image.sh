#!/usr/bin/env bash
# Dong goi image thanh 1 file de phan phoi (docker save + gzip).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
IMAGE="${IMAGE:-legal-mcp:latest}"
OUT="${1:-legal-mcp-image.tar.gz}"
echo "Dang luu $IMAGE -> $OUT ..."
docker save "$IMAGE" | gzip > "$OUT"
ls -lh "$OUT"
echo "Ben may dich: gunzip -c $OUT | docker load"
echo "Chay: docker run -d --name legal-mcp -p 8000:8000 -e EMBED_API_KEY=sk-xxxx $IMAGE"
