#!/usr/bin/env bash
set -e
docker rm -f lm-fix4 2>/dev/null || true
docker create --name lm-fix4 legal-mcp:latest >/dev/null
docker commit \
  --change 'ENTRYPOINT ["/app/entrypoint.sh"]' \
  --change 'CMD []' \
  lm-fix4 legal-mcp:latest >/dev/null
docker rm lm-fix4 >/dev/null
echo "ENTRYPOINT RESTORED:"
docker inspect legal-mcp:latest --format 'EP={{.Config.Entrypoint}} CMD={{.Config.Cmd}}'

echo "=== TEST LAI CONTAINER ==="
docker rm -f legal-mcp-final 2>/dev/null || true
docker run -d --name legal-mcp-final -p 8002:8000 -e EMBED_API_KEY=sk-1234 legal-mcp:latest >/dev/null
echo "started, doi 90s de load 378k docs..."
sleep 90
docker ps -a --filter name=legal-mcp-final --format '{{.Status}}'
docker logs legal-mcp-final 2>&1 | tail -4
