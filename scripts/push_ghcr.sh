#!/usr/bin/env bash
# Cho finalize_image xong -> tag -> push ghcr.io/dinhxuantuyen/legal-mcp:latest
# Yeu cau: da `docker login ghcr.io` truoc do (khong luu token trong script nay).
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

IMAGE_LOCAL="legal-mcp:latest"
IMAGE_REMOTE="ghcr.io/dinhxuantuyen/legal-mcp:latest"

echo "[push] $(date '+%F %T') Cho finalize_image hoan tat..."
while pgrep -f '[f]inalize_image' >/dev/null 2>&1; do sleep 30; done

if ! grep -q '\[3/3\]' data/build/finalize.log; then
  echo "[push] LOI: finalize chua chay toi buoc [3/3] — kiem tra data/build/finalize.log"; exit 1
fi
if ! docker image inspect "$IMAGE_LOCAL" >/dev/null 2>&1; then
  echo "[push] LOI: khong thay image $IMAGE_LOCAL"; exit 1
fi

echo "[push] $(date '+%F %T') Image san sang. Tag + push len GHCR..."
docker tag "$IMAGE_LOCAL" "$IMAGE_REMOTE"
docker push "$IMAGE_REMOTE"
echo "[push] $(date '+%F %T') HOAN TAT: $IMAGE_REMOTE"
