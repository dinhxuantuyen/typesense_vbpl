#!/usr/bin/env bash
# Thi nghiem co lap segfault:
# A) host + ts-build-data + --api-port  -> kiem tra data co tot khong
# B) container + --api-port             -> kiem tra flag --listen-port co phai thu pham
cd ~ || exit 1

echo "===== A) HOST: load ts-build-data bang --api-port 8111 ====="
/mnt/d/claude_code/typesense/bin/typesense-server --data-dir ~/ts-build-data \
  --api-key poc_legal_search_2026 --api-port 8111 --peering-port 8112 > ~/ts-hostA.log 2>&1 &
A_PID=$!
for i in $(seq 1 150); do
  if ! kill -0 $A_PID 2>/dev/null; then echo "A: CHET som"; tail -3 ~/ts-hostA.log; break; fi
  N=$(curl -s -m 3 http://localhost:8111/collections/legal_articles -H "X-TYPESENSE-API-KEY: poc_legal_search_2026" 2>/dev/null | grep -o '"num_documents":[0-9]*')
  if [ -n "$N" ]; then echo "A: OK $N (sau ${i}x2s)"; break; fi
  sleep 2
done
kill $A_PID 2>/dev/null; wait $A_PID 2>/dev/null

echo "===== B) CONTAINER: --api-port thay cho --listen-port ====="
docker rm -f lm-exp 2>/dev/null
docker run -d --name lm-exp --entrypoint typesense-server legal-mcp:latest \
  --data-dir /data --api-key poc_legal_search_2026 --api-port 8108 >/dev/null
for i in $(seq 1 150); do
  ST=$(docker ps -a --filter name=lm-exp --format '{{.Status}}')
  echo "$ST" | grep -q Exited && { echo "B: CONTAINER CHET ($ST)"; docker logs lm-exp 2>&1 | tail -3; break; }
  N=$(docker exec lm-exp curl -s -m 3 http://localhost:8108/collections/legal_articles -H "X-TYPESENSE-API-KEY: poc_legal_search_2026" 2>/dev/null | grep -o '"num_documents":[0-9]*')
  if [ -n "$N" ]; then echo "B: OK $N (sau ${i}x2s)"; break; fi
  sleep 2
done
docker rm -f lm-exp 2>/dev/null
echo "===== XONG ====="
