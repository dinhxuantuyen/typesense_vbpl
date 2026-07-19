#!/usr/bin/env bash
echo "=== container legal-mcp dang mount gi ==="
docker inspect legal-mcp --format '{{range .Mounts}}{{.Type}} | {{.Name}} | {{.Source}} -> {{.Destination}}
{{end}}' 2>/dev/null || echo "(container legal-mcp khong ton tai)"

echo "=== docker volume legal-data ==="
docker volume inspect legal-data --format 'Mountpoint: {{.Mountpoint}}' 2>/dev/null || echo "(khong co volume legal-data)"
du -sh /var/lib/docker/volumes/legal-data/_data 2>/dev/null

echo "=== docker root (nam trong ext4 cua WSL) ==="
docker info --format 'Docker Root Dir: {{.DockerRootDir}}' 2>/dev/null

echo "=== ban sao tren C: (file nguon embedded, KHONG phai index song) ==="
ls -lh /mnt/c/legal_backup/ 2>/dev/null || echo "(khong co C:\\legal_backup)"

echo "=== disk cua WSL (/ = ext4.vhdx) ==="
df -h / | tail -1
