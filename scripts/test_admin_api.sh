#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for p in $(pgrep -f "[l]egal_search.admin_api"); do kill "$p" 2>/dev/null; done
sleep 1
setsid nohup ~/legal-venv/bin/python -m legal_search.admin_api > data/build/admin.log 2>&1 < /dev/null &
sleep 6
echo "--- health ---";     curl -s -m 10 http://localhost:8010/health; echo
echo "--- POST /articles (upsert) ---"; curl -s -m 60 -X POST http://localhost:8010/articles --data-binary @data/test_crud.json -H "Content-Type: application/json"; echo
echo "--- GET /articles/{id} ---"; curl -s -m 10 http://localhost:8010/articles/TEST-crud-dieu-1 | head -c 220; echo
echo "--- PATCH /articles/status ---"; curl -s -m 10 -X PATCH http://localhost:8010/articles/status -H "Content-Type: application/json" -d '{"chunk_id":"TEST-crud-dieu-1","validity_status":"Het hieu luc","expiration_date":"2025-01-01"}'; echo
echo "--- DELETE /articles/{id} ---"; curl -s -m 10 -X DELETE http://localhost:8010/articles/TEST-crud-dieu-1; echo
