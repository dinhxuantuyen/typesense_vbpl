#!/usr/bin/env bash
# Chay bang root (qua sudo). Doi DNS sang 8.8.8.8 va ngan WSL ghi de.
set -e
rm -f /etc/resolv.conf
echo "nameserver 8.8.8.8" > /etc/resolv.conf
chattr +i /etc/resolv.conf 2>/dev/null || true   # khoa file de WSL khong ghi de (best-effort)
if ! grep -q "generateResolvConf" /etc/wsl.conf 2>/dev/null; then
  printf '[network]\ngenerateResolvConf = false\n' >> /etc/wsl.conf
fi
echo "=== resolv.conf moi ==="
cat /etc/resolv.conf
