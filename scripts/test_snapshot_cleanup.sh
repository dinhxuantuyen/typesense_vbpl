#!/usr/bin/env bash
echo "=== test snapshot (DEPLOY buoc 4) ==="
docker exec lm-deploy-test bash -c 'curl -s -X POST "http://localhost:8108/operations/snapshot?snapshot_path=/data/backup" -H "X-TYPESENSE-API-KEY: $TYPESENSE_API_KEY"'
echo
echo "=== don dep test ==="
docker rm -f lm-deploy-test >/dev/null 2>&1 && docker volume rm lm-test-data >/dev/null 2>&1 && echo "da don"
echo "=== gzip ==="
ls -lh /mnt/d/claude_code/typesense/data/embedded.jsonl.gz
pgrep -x gzip >/dev/null && echo GZIP_RUNNING || echo GZIP_DONE
