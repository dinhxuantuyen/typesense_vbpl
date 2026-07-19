#!/usr/bin/env bash
cd /mnt/d/claude_code/typesense
tail -3 data/build/import_ms.log
curl -s -m 5 http://localhost:8108/collections/legal_mainstream -H "X-TYPESENSE-API-KEY: poc_legal_search_2026" \
  | python3 -c "import sys,json;print('num_documents =',json.load(sys.stdin).get('num_documents'))"
pgrep -f '[i]mport_mainstream' >/dev/null && echo "import: RUNNING" || echo "import: DONE"
docker stats --no-stream --format '{{.Name}} MEM={{.MemUsage}}' legal-mcp 2>/dev/null
