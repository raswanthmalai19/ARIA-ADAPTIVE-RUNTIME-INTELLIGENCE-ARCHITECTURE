# ARIA Production Deployment Guide

This guide covers deploying ARIA in production environments.

## Quick Start (Docker)

```bash
# Build image
docker build -t aria:latest .

# Run with docker-compose
docker-compose up -d

# Check status
docker-compose logs aria-api
docker exec aria-api curl http://localhost:8000/health
```

## Standalone Deployment (Linux)

### Prerequisites
- Python 3.10+
- 8GB+ RAM
- Apple Silicon/x86_64

### Installation

```bash
# Clone repository
git clone https://github.com/raswanthmalai19/ARIA-ADAPTIVE-RUNTIME-INTELLIGENCE-ARCHITECTURE.git
cd ARIA

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp deployment/.env.example .env
# Edit .env with your settings
```

### Running as Systemd Service

```bash
# Copy service file
sudo cp deployment/aria.service /etc/systemd/system/

# Create aria user
sudo useradd -m -s /bin/bash aria

# Setup directory
sudo mkdir -p /home/aria/aria
sudo chown -R aria:aria /home/aria/aria

# Copy code to service directory
sudo cp -r . /home/aria/aria/

# Enable and start service
sudo systemctl enable aria
sudo systemctl start aria
sudo systemctl status aria

# View logs
sudo journalctl -u aria -f
```

### Nginx Reverse Proxy

```bash
# Copy nginx config
sudo cp deployment/nginx.conf /etc/nginx/sites-available/aria

# Enable site
sudo ln -s /etc/nginx/sites-available/aria /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Kubernetes Deployment

```bash
# Apply manifests
kubectl apply -f deployment/k8s-deployment.yaml

# Check status
kubectl get pods -l app=aria
kubectl get svc aria-api

# View logs
kubectl logs -f deployment/aria-api

# Scale horizontally
kubectl scale deployment aria-api --replicas=5
```

## Environment Variables

```
ARIA_MODEL=qwen2.5-3b          # Model to use
ARIA_EXECUTION_MODE=dynamic_layers  # dynamic_layers, cascade, standard
ARIA_CACHE_SIZE=1000            # Max inference cache entries
ARIA_LOG_LEVEL=info             # debug, info, warning, error
ARIA_PORT=8000                  # API port
ARIA_WORKERS=4                  # Worker processes
```

## Monitoring

### Health Endpoint
```bash
curl http://localhost:8000/health
```

### Metrics (Prometheus)
```bash
curl http://localhost:8000/metrics
```

### Log Levels
- `debug` - Detailed debugging info
- `info` - General info messages
- `warning` - Warning messages
- `error` - Error messages only

## Performance Tuning

### Memory Optimization
```bash
# For systems with limited RAM, reduce cache
ARIA_CACHE_SIZE=100
```

### Concurrency
```bash
# Increase workers for more throughput
ARIA_WORKERS=8
```

### Model Selection
```bash
# Use smaller model for lower latency/memory
ARIA_MODEL=qwen2.5-0.5b

# Use larger model for better quality
ARIA_MODEL=qwen2.5-7b
```

## Troubleshooting

### Port Already in Use
```bash
# Find and kill process
lsof -i :8000
kill -9 <PID>
```

### Out of Memory
```bash
# Check memory usage
free -h
docker stats aria-api

# Reduce cache size
ARIA_CACHE_SIZE=50
```

### Model Not Loading
```bash
# Check model cache
ls -la models_cache/

# Clear cache
rm -rf models_cache/

# Re-download model
python -c "from aria.engine import ARIAEngine; engine = ARIAEngine(); engine.initialize()"
```

## Security Considerations

- Run as non-root user ✅
- Enable HTTPS/TLS ✅
- Use nginx reverse proxy ✅
- Implement rate limiting ✅
- Restrict API access by IP
- Use API keys for authentication
- Regularly update dependencies
- Monitor logs for suspicious activity

## Backup & Recovery

```bash
# Backup model cache
tar -czf aria-models-backup.tar.gz models_cache/

# Backup configuration
cp .env aria-config-backup.env

# Restore
tar -xzf aria-models-backup.tar.gz
cp aria-config-backup.env .env
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/raswanthmalai19/ARIA-ADAPTIVE-RUNTIME-INTELLIGENCE-ARCHITECTURE/issues
- Email: raswanthmalaisamy@gmail.com
