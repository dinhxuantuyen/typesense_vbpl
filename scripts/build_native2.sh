#!/usr/bin/env bash
# Build image tu native FS — dung rsync resumable cho ts-data 16GB.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# don tien trinh build cu neu con
for p in $(pgrep -f '[b]uild_native.sh'); do kill "$p" 2>/dev/null || true; done

CTX=~/legal-build-ctx
mkdir -p "$CTX/bin" "$CTX/data/build"
cp Dockerfile requirements.txt "$CTX/"
cp -r legal_search docker "$CTX/"
cp bin/typesense-server "$CTX/bin/" 2>/dev/null || true

echo "[native2] rsync ts-data (resume phan da copy)..."
rsync -a --info=progress2 data/build/ts-data/ "$CTX/data/build/ts-data/" 2>&1 | tail -2
echo "[native2] context size:"; du -sh "$CTX"

echo "[native2] docker build..."
cd "$CTX"
docker build -t legal-mcp:latest . 2>&1 | tail -12
echo "[native2] KET QUA:"
docker images legal-mcp --format '{{.Repository}}:{{.Tag}} {{.Size}}'
