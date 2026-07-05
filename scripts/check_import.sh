#!/usr/bin/env bash
PORT="${1:-8108}"
curl -s -m 5 "http://localhost:$PORT/collections/legal_articles" -H "X-TYPESENSE-API-KEY: poc_legal_search_2026" | grep -o '"num_documents":[0-9]*'
uptime | awk '{print "uptime:", $3, $4}'
tail -2 /mnt/d/claude_code/typesense/data/build/deploy_local.log 2>/dev/null
