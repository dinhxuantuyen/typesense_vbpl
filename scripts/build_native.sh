#!/usr/bin/env bash
# Build image tu native FS (~/legal-build-ctx) — tranh drvfs cham/loi voi context 16GB.
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."

CTX=~/legal-build-ctx
echo "[native] Chuan bi context tai $CTX ..."
rm -rf "$CTX"
mkdir -p "$CTX"
cp Dockerfile requirements.txt "$CTX/"
cp -r legal_search docker "$CTX/"
mkdir -p "$CTX/bin"
cp bin/typesense-server "$CTX/bin/"
echo "[native] Copy ts-data (16GB) sang native FS..."
mkdir -p "$CTX/data/build"
time cp -r data/build/ts-data "$CTX/data/build/ts-data"
du -sh "$CTX"

echo "[native] docker build..."
cd "$CTX"
docker build -t legal-mcp:latest . 2>&1 | tail -15
echo "[native] BUILD XONG:"
docker images legal-mcp --format '{{.Repository}}:{{.Tag}} {{.Size}}'
