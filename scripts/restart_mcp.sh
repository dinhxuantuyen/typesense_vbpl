#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for p in $(pgrep -f "[m]cp_server"); do kill "$p" 2>/dev/null; done
sleep 2
setsid nohup ~/legal-venv/bin/python -m legal_search.mcp_server > data/build/mcp.log 2>&1 < /dev/null &
sleep 6
echo "--- mcp.log ---"
tail -4 data/build/mcp.log
pgrep -f "[m]cp_server" >/dev/null && echo "MCP RUNNING" || echo "MCP FAILED"
