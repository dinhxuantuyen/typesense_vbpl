#!/usr/bin/env bash
echo "=== /etc/resolv.conf ==="
cat /etc/resolv.conf
echo "=== dockerd process (co o distro nay khong?) ==="
ps aux | grep -i '[d]ockerd' || echo "khong thay dockerd trong distro nay (co the la Docker Desktop)"
echo "=== docker info (server) ==="
docker info 2>/dev/null | grep -iE 'Operating System|Server Version|Name:'
echo "=== docker context ==="
docker context ls 2>/dev/null
echo "=== retry pull ==="
docker pull python:3.12-slim-bookworm 2>&1 | tail -3
