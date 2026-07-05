#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PYTHONIOENCODING=utf-8
echo "===== 1) UPSERT (them dieu test, re-embed) ====="
python3 -m legal_search.crud upsert --file data/test_crud.json
echo "===== 2) GET (mong doi: co, is_effective_now=true) ====="
python3 -m legal_search.crud get --chunk-id TEST-crud-dieu-1
echo "===== 3) PATCH hieu luc (het hieu luc, expiration qua khu) ====="
python3 -m legal_search.crud patch-status --chunk-id TEST-crud-dieu-1 --status "Het hieu luc" --expiration 2025-01-01
echo "===== 4) GET (mong doi: status doi, is_effective_now=false) ====="
python3 -m legal_search.crud get --chunk-id TEST-crud-dieu-1
echo "===== 5) DELETE ====="
python3 -m legal_search.crud delete --chunk-id TEST-crud-dieu-1
echo "===== 6) GET (mong doi: null - da xoa) ====="
python3 -m legal_search.crud get --chunk-id TEST-crud-dieu-1
