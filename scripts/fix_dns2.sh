#!/usr/bin/env bash
# Chay bang root. Dung CA HAI nameserver: 10.255.255.254 (phan giai proxy noi bo)
# + 8.8.8.8 (du phong cho docker registry).
set -e
chattr -i /etc/resolv.conf 2>/dev/null || true
printf 'nameserver 10.255.255.254\nnameserver 8.8.8.8\n' > /etc/resolv.conf
chattr +i /etc/resolv.conf 2>/dev/null || true
echo "=== resolv.conf ==="; cat /etc/resolv.conf
echo "=== resolve proxy.cyberbot.vn ==="; getent hosts proxy.cyberbot.vn || echo "PROXY RESOLVE FAIL"
echo "=== resolve registry-1.docker.io ==="; getent hosts registry-1.docker.io | head -1 || echo "REGISTRY RESOLVE FAIL"
