#!/usr/bin/env bash
echo "=== build_native2 process tree ==="
PID=$(pgrep -f '[b]uild_native2.sh' | head -1)
echo "script PID=$PID"
if [ -n "$PID" ]; then
  ps -o pid,stat,etime,cmd --ppid "$PID"
  echo "--- wchan ---"; cat /proc/$PID/wchan 2>/dev/null; echo
fi
echo "=== moi tien trinh docker client ==="
ps aux | grep -v grep | grep -E 'docker (build|push|tag)' || echo "khong co docker client nao"
echo "=== dockerd co dang nhan context? (tmp dir) ==="
sudo -n du -sh /var/lib/docker/tmp 2>/dev/null || du -sh /var/lib/docker/tmp 2>/dev/null || echo "khong doc duoc /var/lib/docker/tmp"
