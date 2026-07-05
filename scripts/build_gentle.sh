#!/usr/bin/env bash
# Build image theo cach "nhe nhang": slim image + docker cp tung part + commit tung layer.
# Ly do: WSL Service crash duoi I/O burst lon; moi buoc <6GB + nghi giua cac buoc.
# Dong thoi moi layer <10GB (gioi han GHCR).
set -e
cd ~/legal-build-ctx

echo "=== [1/5] Build SLIM image (khong co data) ==="
# Dockerfile slim: bo 3 dong COPY part
sed '/^COPY part[123]\/ \/data\/$/d' Dockerfile > Dockerfile.slim
docker build -t legal-mcp:slim -f Dockerfile.slim . 2>&1 | tail -3

echo "=== [2/5] cp part1 ($(du -sh part1 | cut -f1)) + commit ==="
docker rm -f lm-stage 2>/dev/null || true
docker create --name lm-stage legal-mcp:slim >/dev/null
docker cp part1/. lm-stage:/data/
docker commit lm-stage legal-mcp:stage1 >/dev/null
docker rm -f lm-stage >/dev/null
sleep 10

echo "=== [3/5] cp part2 ($(du -sh part2 | cut -f1)) + commit ==="
docker create --name lm-stage legal-mcp:stage1 >/dev/null
docker cp part2/. lm-stage:/data/
docker commit lm-stage legal-mcp:stage2 >/dev/null
docker rm -f lm-stage >/dev/null
sleep 10

echo "=== [4/5] cp part3 ($(du -sh part3 | cut -f1)) + commit ==="
docker create --name lm-stage legal-mcp:stage2 >/dev/null
docker cp part3/. lm-stage:/data/
docker commit lm-stage legal-mcp:latest >/dev/null
docker rm -f lm-stage >/dev/null

echo "=== [5/5] don image trung gian ==="
docker rmi legal-mcp:stage1 legal-mcp:stage2 2>/dev/null || true
docker images legal-mcp --format '{{.Repository}}:{{.Tag}} {{.Size}}'
echo "=== HOAN TAT ==="
