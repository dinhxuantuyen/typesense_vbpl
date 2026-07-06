#!/usr/bin/env bash
set -e
cd "$(dirname "${BASH_SOURCE[0]}")/.."
echo "=== verify import trong venv ==="
~/legal-venv/bin/python -c "from mcp.server.transport_security import TransportSecuritySettings; print('import OK')"
echo "=== cap nhat file vao container ==="
cp legal_search/mcp_server.py /tmp/mcp_server.py
sed -i 's/\r$//' /tmp/mcp_server.py
docker cp /tmp/mcp_server.py legal-mcp:/app/legal_search/mcp_server.py
cp legal_search/search.py /tmp/search.py     # kem luon fix doc-code routing hom nay
sed -i 's/\r$//' /tmp/search.py
docker cp /tmp/search.py legal-mcp:/app/legal_search/search.py
echo "=== restart container (typesense load lai snapshot) ==="
docker restart legal-mcp >/dev/null
echo "restarted. Theo doi: docker logs -f legal-mcp"
