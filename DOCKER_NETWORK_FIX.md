# Docker TLS Timeout Fix

## Problem
`TLS handshake timeout` when pulling base images from Docker Hub during `docker compose up -d --build`

## Solution 1: Configure Docker Daemon (Recommended)

### macOS (Docker Desktop)
1. Open Docker Desktop → Settings → Docker Engine
2. Add the following to the JSON config:
```json
{
  "registry-mirrors": [
    "https://mirror.gcr.io",
    "https://hub-mirror.c.163.com"
  ],
  "max-concurrent-downloads": 3
}
```
3. Click "Apply & Restart"

### Linux
1. Edit `/etc/docker/daemon.json`:
```bash
sudo nano /etc/docker/daemon.json
```
2. Add:
```json
{
  "registry-mirrors": [
    "https://mirror.gcr.io",
    "https://hub-mirror.c.163.com"
  ],
  "max-concurrent-downloads": 3
}
```
3. Restart Docker:
```bash
sudo systemctl restart docker
```

### Windows (Docker Desktop)
1. Right-click Docker Desktop → Settings
2. Resources → Docker Engine
3. Add the JSON config (same as macOS)
4. Click "Apply & Restart"

## Solution 2: Retry Build with Backoff

```bash
bash docker-build-retry.sh
```

This will retry up to 3 times with exponential backoff.

## Solution 3: Pre-pull Base Images

```bash
docker pull python:3.11-slim
docker pull node:20-alpine
docker compose up -d --build
```

## Solution 4: Increase Docker Client Timeout

```bash
DOCKER_CLIENT_TIMEOUT=120 COMPOSE_HTTP_TIMEOUT=120 docker compose up -d --build
```

## Verify Connection

```bash
docker pull python:3.11-slim
```

If this fails, Docker connectivity to Hub is the issue (not code-related).
