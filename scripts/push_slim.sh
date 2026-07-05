#!/usr/bin/env bash
# Build slim image tu repo + push GHCR.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "=== [1/3] don container test cu ==="
docker rm -f legal-mcp-final lm-exp lm-patch 2>/dev/null || true

echo "=== [2/3] build slim (context D:, nho) ==="
docker build -t legal-mcp:slim -f Dockerfile.slim . 2>&1 | tail -3

echo "=== [3/3] tag + push GHCR ==="
docker tag legal-mcp:slim ghcr.io/dinhxuantuyen/legal-mcp:slim
docker push ghcr.io/dinhxuantuyen/legal-mcp:slim 2>&1 | tail -4
echo "=== PUSH XONG: ghcr.io/dinhxuantuyen/legal-mcp:slim ==="
