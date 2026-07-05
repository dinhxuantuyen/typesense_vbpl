#!/usr/bin/env bash
echo "=== uptime WSL ==="; uptime
echo "=== RAM ==="; free -h | head -2
echo "=== OOM kills gan day ==="
dmesg -T 2>/dev/null | grep -iE 'out of memory|oom|killed process' | tail -6
[ ${PIPESTATUS[0]} -ne 0 ] && sudo -n dmesg -T 2>/dev/null | grep -iE 'out of memory|oom|killed process' | tail -6
echo "=== typesense live (8108)? ==="; curl -s -m 5 http://localhost:8108/health || echo FAIL
echo
echo "=== mcp (8000)? ==="; curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://localhost:8000/mcp || echo FAIL
echo "=== docker containers ==="; docker ps --format '{{.Names}} {{.Status}}' | head -6
echo "=== disk / ==="; df -h / | tail -1
