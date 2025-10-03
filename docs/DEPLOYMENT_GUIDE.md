# Production Deployment Guide

**Version**: Post Bug-Fix Release (2025-10-03)
**Status**: ✅ Production Ready
**Commit**: `9947da8`

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Security Configuration](#security-configuration)
4. [Deployment Steps](#deployment-steps)
5. [Monitoring & Logging](#monitoring--logging)
6. [Performance Tuning](#performance-tuning)
7. [Troubleshooting](#troubleshooting)
8. [Rollback Plan](#rollback-plan)

---

## Prerequisites

### System Requirements

**Minimum**:
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 20GB SSD
- **OS**: Linux (Ubuntu 20.04+), macOS, Windows Server 2019+

**Recommended**:
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 50GB+ SSD
- **OS**: Linux (Ubuntu 22.04 LTS)

### Software Dependencies

```bash
# Python 3.10 or higher
python --version  # Must be 3.10+

# Ollama (if using local LLM)
ollama --version

# Git
git --version
```

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/ollama-rag.git
cd ollama-rag
git checkout master  # Or specific release tag
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
.\venv\Scripts\activate

# Install packages
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Variables

Create `.env` file in project root:

```bash
# ===== LLM Configuration =====
PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
EMBED_MODEL=nomic-embed-text

# ===== Database Configuration =====
PERSIST_ROOT=data/kb
DB_NAME=default
VECTOR_BACKEND=chroma

# ===== CORS Configuration (IMPORTANT!) =====
# ❌ DO NOT USE WILDCARDS!
CORS_ORIGINS=http://localhost:8000,http://localhost:3000,https://yourdomain.com

# ===== Performance Configuration =====
GEN_CACHE_ENABLE=1
GEN_CACHE_TTL=86400

# ===== Rate Limiting =====
RATE_LIMIT_QUERY=10/minute
RATE_LIMIT_INGEST=5/minute
RATE_LIMIT_UPLOAD=3/minute

# ===== Logging =====
LOG_LEVEL=INFO
```

---

## Security Configuration

### 🔴 Critical Security Settings

#### 1. CORS Origins (Mandatory)

```bash
# ✅ CORRECT - Explicit origins only
CORS_ORIGINS="https://app.example.com,https://api.example.com"

# ❌ WRONG - Never use wildcard!
CORS_ORIGINS="*"  # SECURITY VULNERABILITY!
```

#### 2. Secure Logging

Sensitive data is automatically redacted, but verify:

```bash
# Check logs don't contain plaintext secrets
grep -i "password\|token\|api_key" logs/app.log | grep -v "REDACTED"
# Should return nothing
```

#### 3. Path Validation

```bash
# Ensure base directory is absolute
export PERSIST_ROOT="/var/lib/ollama-rag/kb"  # Absolute path
```

#### 4. Rate Limiting

```bash
# Adjust based on expected load
RATE_LIMIT_QUERY=100/minute  # For production
RATE_LIMIT_INGEST=10/minute
RATE_LIMIT_UPLOAD=5/minute
```

---

## Deployment Steps

### Option A: Development/Testing

```bash
# Start server (development)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option B: Production (Gunicorn + Uvicorn Workers)

#### 1. Install Production Server

```bash
pip install gunicorn
```

#### 2. Create Systemd Service (Linux)

Create `/etc/systemd/system/ollama-rag.service`:

```ini
[Unit]
Description=Ollama RAG API Server
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/ollama-rag
Environment="PATH=/opt/ollama-rag/venv/bin"
EnvironmentFile=/opt/ollama-rag/.env
ExecStart=/opt/ollama-rag/venv/bin/gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300 \
    --access-logfile /var/log/ollama-rag/access.log \
    --error-logfile /var/log/ollama-rag/error.log \
    app.main:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Start Service

```bash
# Create log directory
sudo mkdir -p /var/log/ollama-rag
sudo chown www-data:www-data /var/log/ollama-rag

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ollama-rag
sudo systemctl start ollama-rag

# Check status
sudo systemctl status ollama-rag
```

### Option C: Docker Deployment

#### 1. Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p data/kb

# Expose port
EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "app.main:app"]
```

#### 2. Build and Run

```bash
# Build image
docker build -t ollama-rag:latest .

# Run container
docker run -d \
  --name ollama-rag \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e CORS_ORIGINS="https://yourdomain.com" \
  --restart unless-stopped \
  ollama-rag:latest
```

### Option D: Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ollama-rag:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - CORS_ORIGINS=https://yourdomain.com
      - OLLAMA_BASE_URL=http://ollama:11434
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

volumes:
  ollama_data:
```

Deploy:
```bash
docker-compose up -d
docker-compose logs -f ollama-rag
```

---

## Monitoring & Logging

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-10-03T08:00:00Z",
  "db": "default",
  "ollama_connected": true,
  "db_exists": true,
  "version": "0.3.1"
}
```

### Log Monitoring

#### Application Logs

```bash
# Watch logs (systemd)
sudo journalctl -u ollama-rag -f

# Watch logs (Docker)
docker logs -f ollama-rag

# Search for errors
grep ERROR /var/log/ollama-rag/error.log
```

#### Security Audit

```bash
# Verify sensitive data redaction
grep -i "redacted" /var/log/ollama-rag/access.log

# Check for CORS misconfigurations
grep -i "cors wildcard" /var/log/ollama-rag/error.log

# Monitor rate limiting
grep -i "rate limit" /var/log/ollama-rag/access.log
```

### Performance Monitoring

#### Prometheus Metrics (Optional)

Install `prometheus-fastapi-instrumentator`:

```bash
pip install prometheus-fastapi-instrumentator
```

Add to `app/main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

# After app creation
Instrumentator().instrument(app).expose(app)
```

Metrics available at: `http://localhost:8000/metrics`

#### Key Metrics to Monitor

- **Request latency**: `<50ms` for simple queries
- **Analytics response time**: `<50ms` for 100 chats
- **Memory usage**: `<2GB` for typical workload
- **Cache hit rate**: `>80%` for repeated queries
- **Error rate**: `<1%`

---

## Performance Tuning

### Worker Configuration

```bash
# Calculate optimal workers
# Formula: (2 x CPU cores) + 1
NUM_WORKERS=$(python -c "import os; print((2 * os.cpu_count()) + 1)")

# For 4 cores: 9 workers
gunicorn --workers $NUM_WORKERS ...
```

### Database Performance

```bash
# Enable FAISS for faster vector search (optional)
export VECTOR_BACKEND=faiss
pip install faiss-cpu
```

### Cache Configuration

```bash
# Tune cache settings in .env
GEN_CACHE_ENABLE=1
GEN_CACHE_TTL=86400  # 24 hours

# LRU cache is automatically managed (max 100 items, 5min TTL)
```

### Connection Pooling

For high-concurrency scenarios:

```python
# In app/main.py, increase uvicorn limits
uvicorn app.main:app \
  --workers 4 \
  --limit-concurrency 1000 \
  --limit-max-requests 10000
```

---

## Troubleshooting

### Common Issues

#### 1. CORS Errors in Browser

**Symptom**: Browser console shows CORS errors

**Fix**:
```bash
# Check CORS configuration
echo $CORS_ORIGINS

# Ensure it includes your frontend domain
CORS_ORIGINS="https://your-frontend.com"
```

#### 2. Slow Analytics Queries

**Symptom**: Analytics endpoint takes >5 seconds

**Check**:
```python
# Run test to verify bulk fetch optimization
python test_all_bugs.py  # Should show <50ms for analytics
```

**Fix**: Ensure commit `9947da8` is deployed (N+1 query fix included)

#### 3. Memory Growth Over Time

**Symptom**: Memory usage increases continuously

**Check**:
```bash
# Monitor memory
ps aux | grep gunicorn

# Check cache is bounded
# Should see LRU cache in logs, not unbounded dict
```

**Fix**: Ensure LRU cache with TTL is active (automatic in bug fix release)

#### 4. Server Unresponsive During Uploads

**Symptom**: Other requests blocked during file upload

**Check**:
```bash
# Verify aiofiles is installed
pip show aiofiles
```

**Fix**: Ensure async I/O is enabled (automatic in bug fix release)

#### 5. Race Condition Crashes

**Symptom**: BM25 initialization errors with concurrent requests

**Fix**: Ensure thread-safe double-checked locking is active (included in bug fix)

---

## Rollback Plan

### Quick Rollback

```bash
# Stop service
sudo systemctl stop ollama-rag  # or docker-compose down

# Revert to previous version
git revert 9947da8
git push origin master

# Reinstall dependencies (if needed)
pip install -r requirements.txt

# Restart service
sudo systemctl start ollama-rag  # or docker-compose up -d
```

### Database Rollback

No database migrations in this release. All changes are backward compatible.

---

## Production Checklist

Before going live:

- [ ] `.env` file configured with production values
- [ ] CORS origins set to explicit domains (no wildcards!)
- [ ] SSL/TLS certificate installed (use Let's Encrypt or similar)
- [ ] Firewall configured (allow only 80/443, block 8000 from internet)
- [ ] Reverse proxy setup (Nginx/Caddy) with rate limiting
- [ ] Health check endpoint verified
- [ ] Log rotation configured
- [ ] Monitoring alerts setup
- [ ] Backup strategy defined for `data/kb` directory
- [ ] Load testing completed
- [ ] Security scan passed (no CORS/path traversal vulns)
- [ ] Documentation reviewed by team
- [ ] Rollback plan tested

---

## Security Hardening

### Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Support

For issues or questions:
- **Documentation**: Check `docs/BUG_FIXES_2025_10_03.md`
- **Testing**: Run `python test_all_bugs.py` to verify deployment
- **Logs**: Check `/var/log/ollama-rag/` for errors
- **GitHub**: Open issue with deployment logs and config (redact secrets!)

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-10-03
**Version**: Post Bug-Fix Release (Commit 9947da8)
