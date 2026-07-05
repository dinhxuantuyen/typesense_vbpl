#!/usr/bin/env bash
PID=$(pgrep -x cp | head -1)
if [ -z "$PID" ]; then echo "khong co tien trinh cp"; exit 0; fi
echo "cp PID=$PID"
A=$(awk '/rchar/{print $2}' /proc/$PID/io)
sleep 6
B=$(awk '/rchar/{print $2}' /proc/$PID/io)
echo "rchar delta 6s = $(( (B-A)/1024/1024 )) MB/6s"
ls -l /proc/$PID/fd 2>/dev/null | grep -oE '/home.*|/mnt.*' | tail -3
