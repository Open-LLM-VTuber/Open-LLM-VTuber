# Open-LLM-VTuber Docker Deployment

Quick start with Docker for production-grade deployment.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2+
- (Optional) NVIDIA Container Toolkit for GPU acceleration

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git
cd Open-LLM-VTuber

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Check service status
docker-compose ps
```

## Access

- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Grafana Metrics: http://localhost:3000 (admin/vtuber)
- Redis: localhost:6379
- OTEL Collector: localhost:4317

## GPU Acceleration

If NVIDIA GPU is available, install Container Toolkit first:

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## Data Persistence

All persistent data is stored in Docker volumes:

| Volume | Path | Contents |
|---|---|---|
| vtuber-data | `./data` | SQLite database, user data |
| vtuber-cache | `./cache` | Audio cache, model cache |
| redis-data | Named volume | Redis persistence |
| grafana-data | Named volume | Metrics dashboards |

## Configuration

Environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|---|---|---|
| DATABASE_URL | sqlite+aiosqlite:///data/vtuber.db | Database connection string |
| REDIS_HOST | redis | Redis server address |
| REDIS_PORT | 6379 | Redis port |
| OTEL_EXPORTER_OTLP_ENDPOINT | http://otel:4317 | OpenTelemetry collector |

## Monitoring

Grafana dashboards track:
- WebSocket connections (active, per-client)
- TTS/ASR latency histograms
- Cache hit/miss rates
- Error rates
- Agent/LLM request latency

## Logging

```bash
# View all service logs
docker-compose logs -f

# View specific service
docker-compose logs -f vtuber
docker-compose logs -f redis
docker-compose logs -f otel
```

## Updating

```bash
docker-compose pull
docker-compose up -d
```

## Backup

```bash
# Backup database
docker-compose exec vtuber cp data/vtuber.db ./backup.db

# Backup Redis
docker-compose exec redis redis-cli BGSAVE
docker-compose cp redis:/data/dump.rdb ./redis-backup.rdb
```

## Troubleshooting

| Issue | Solution |
|---|---|
| Port 8000 already in use | Change port in docker-compose.yml |
| GPU not detected | Verify NVIDIA Container Toolkit installed |
| Redis connection refused | `docker-compose logs redis` |
| Model not loading | Check `./live2d-models/` directory |
| Out of memory | Increase Docker memory limit |