#!/usr/bin/env bash
curl -s -m 5 "http://localhost:8109/collections/legal_articles" -H "X-TYPESENSE-API-KEY: poc_legal_search_2026" | grep -o '"num_documents":[0-9]*'
uptime | awk '{print "uptime:", $3, $4}'
