#!/usr/bin/env bash
# Test them citation vao query_by (khong can re-index)
curl -s -m 15 "http://localhost:8108/multi_search" -X POST \
  -H "X-TYPESENSE-API-KEY: poc_legal_search_2026" -H "Content-Type: application/json" \
  -d '{"searches":[{"collection":"legal_articles","q":"nghi dinh 141/2026/ND-CP","query_by":"citation,heading_ascii,body_ascii","query_by_weights":"5,3,1","per_page":5,"exclude_fields":"embedding","filter_by":"is_low_value:false"}]}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
for h in d['results'][0].get('hits', []):
    doc = h['document']
    print(doc.get('citation'), '|', (doc.get('article_heading') or '')[:60])
"
