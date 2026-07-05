#!/usr/bin/env bash
PID=$(pgrep -f '[l]egal_search.embed_offline' | head -1)
if [ -z "$PID" ]; then echo "EMBED NOT RUNNING"; exit 0; fi
echo "PID=$PID"
echo "cmd: $(tr '\0' ' ' < /proc/$PID/cmdline)"
echo "--- rchar (doc file?) t0 ---"; grep -E 'rchar|wchar' /proc/$PID/io
echo "--- connections toi proxy (dang goi embed?) ---"; ss -tnp 2>/dev/null | grep "pid=$PID" | head -5 || echo "khong co connection"
CPU0=$(awk '{print $14+$15}' /proc/$PID/stat)
sleep 5
CPU1=$(awk '{print $14+$15}' /proc/$PID/stat)
echo "--- sau 5s ---"; grep -E 'rchar' /proc/$PID/io
echo "CPU ticks delta (5s): $((CPU1-CPU0))  (cao=ban CPU/skip-scan, ~0=cho I/O proxy)"
echo "--- wchan (dang cho gi) ---"; cat /proc/$PID/wchan 2>/dev/null; echo
