#!/usr/bin/env bash
# Phuc hoi sau khi WSL restart: build image tu context da co + khoi dong lai dich vu.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "=== [1] docker build tu ~/legal-build-ctx (da rsync xong truoc do) ==="
cd ~/legal-build-ctx
nohup docker build -t legal-mcp:latest . > /mnt/d/claude_code/typesense/data/build/docker_build.log 2>&1 &
BUILD_PID=$!
echo "docker build PID=$BUILD_PID (log: data/build/docker_build.log)"

cd /mnt/d/claude_code/typesense
echo "=== [2] khoi dong lai Typesense live ==="
rm -f typesense.pid
bash scripts/typesense.sh start
sleep 5
bash scripts/typesense.sh health

echo "=== [3] khoi dong lai MCP ==="
bash scripts/restart_mcp.sh | tail -2

echo "=== [4] khoi dong lai dashboard ==="
docker start typesense-dashboard 2>/dev/null && echo "dashboard OK" || echo "dashboard: can chay lai container"
