# Deployment Guide

**Last Updated:** 2025-11-15
**Target Audience:** DevOps, System Administrators
**Difficulty:** Intermediate to Advanced

## Table of Contents

- [Overview](#overview)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Environment Variables](#environment-variables)
- [Deploying Music Tools](#deploying-music-tools)
- [Deploying Tag Editor](#deploying-tag-editor)
- [Deploying EDM Scraper](#deploying-edm-scraper)
- [Production Considerations](#production-considerations)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers deploying the Music Tools Suite applications in production environments. Each application can be deployed independently or together on the same system.

### Deployment Models

| Model | Description | Use Case |
|-------|-------------|----------|
| **Standalone** | Single app on dedicated server | Production with high load |
| **Co-located** | Multiple apps on one server | Development/testing |
| **Docker** | Containerized deployment | Cloud/Kubernetes |
| **Serverless** | Function-based deployment | Event-driven workflows |

---

## Pre-Deployment Checklist

### System Requirements

- [ ] **Python 3.8+** installed
- [ ] **pip** package manager
- [ ] **Virtual environment** support
- [ ] **Git** (for source deployment)
- [ ] **Sufficient disk space** (2GB minimum)
- [ ] **Network access** to APIs (Spotify, Deezer)

### Security Requirements

- [ ] **API credentials** secured
- [ ] **Environment variables** configured
- [ ] **File permissions** set correctly (600/700)
- [ ] **Firewall rules** configured
- [ ] **SSL/TLS** enabled (for web interfaces)
- [ ] **Secrets management** system in place

### Access Requirements

- [ ] **GitHub access** (for private repositories)
- [ ] **API access** confirmed (Spotify, Deezer)
- [ ] **Database permissions** (if using external DB)
- [ ] **File system access** to music library (for Tag Editor)

---

## Environment Variables

### Shared Configuration

All applications require these base environment variables:

```bash
# Application paths
MUSIC_TOOLS_CONFIG_DIR=/var/lib/music-tools/config
MUSIC_TOOLS_DATA_DIR=/var/lib/music-tools/data
MUSIC_TOOLS_LOG_DIR=/var/log/music-tools

# Python environment
PYTHONPATH=/opt/music-tools
PYTHONUNBUFFERED=1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json  # or 'text'
```

### Application-Specific Variables

#### Music Tools

```bash
# Spotify API
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=https://your-domain.com/callback

# Deezer
DEEZER_EMAIL=your_deezer_email@example.com

# Database
DATABASE_PATH=/var/lib/music-tools/data/music_tools.db
```

#### Tag Editor

```bash
# Last.fm (optional)
LASTFM_API_KEY=your_lastfm_api_key

# Music library
MUSIC_LIBRARY_PATH=/mnt/music
CACHE_FILE=/var/lib/music-tools/data/country_cache.json

# Note: Uses Claude via Claude Max plan (no API key needed)
```

#### EDM Scraper

```bash
# Output paths
EDM_OUTPUT_DIR=/var/lib/music-tools/data/edm-scraper
EDM_CACHE_DIR=/var/lib/music-tools/cache/edm-scraper

# Scraper settings
USER_AGENT=Mozilla/5.0 (compatible; MusicToolsBot/1.0)
REQUEST_TIMEOUT=30
```

### Secrets Management

#### Using systemd Environment Files

```bash
# /etc/music-tools/music-tools.env
SPOTIPY_CLIENT_ID=abc123
SPOTIPY_CLIENT_SECRET=xyz789
DEEZER_EMAIL=user@example.com
```

**Secure permissions:**
```bash
sudo chown root:music-tools /etc/music-tools/music-tools.env
sudo chmod 640 /etc/music-tools/music-tools.env
```

#### Using Vault (Recommended for Production)

```bash
# Store secrets in Vault
vault kv put secret/music-tools/spotify \
  client_id=abc123 \
  client_secret=xyz789

# Read in application
export SPOTIPY_CLIENT_ID=$(vault kv get -field=client_id secret/music-tools/spotify)

# Note: Country Tagger uses Claude via Claude Max plan (no API key needed)
```

---

## Deploying Music Tools

### Installation

#### 1. Create Deployment User

```bash
# Create dedicated user
sudo useradd -r -s /bin/bash -d /opt/music-tools music-tools

# Create directories
sudo mkdir -p /opt/music-tools
sudo mkdir -p /var/lib/music-tools/{config,data,cache}
sudo mkdir -p /var/log/music-tools

# Set ownership
sudo chown -R music-tools:music-tools /opt/music-tools
sudo chown -R music-tools:music-tools /var/lib/music-tools
sudo chown -R music-tools:music-tools /var/log/music-tools
```

#### 2. Clone and Install

```bash
# Switch to deployment user
sudo su - music-tools

# Clone repository
cd /opt/music-tools
git clone <repository-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install shared library (required first)
cd packages/common
pip install .

# Install application
cd ../../apps/music-tools
pip install .
```

**Note:** For production deployments, omit the `-e` flag to install packages normally instead of in editable mode.

#### 3. Configure Environment

```bash
# Create environment file
sudo vim /etc/music-tools/music-tools.env

# Add variables
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=https://your-domain.com/callback
DEEZER_EMAIL=your_email@example.com
MUSIC_TOOLS_CONFIG_DIR=/var/lib/music-tools/config

# Secure permissions
sudo chmod 640 /etc/music-tools/music-tools.env
```

#### 4. Create systemd Service

```bash
# Create service file
sudo vim /etc/systemd/system/music-tools.service
```

```ini
[Unit]
Description=Music Tools Service
After=network.target

[Service]
Type=simple
User=music-tools
Group=music-tools
WorkingDirectory=/opt/music-tools/apps/music-tools
Environment=PATH=/opt/music-tools/venv/bin:/usr/bin
EnvironmentFile=/etc/music-tools/music-tools.env
ExecStart=/opt/music-tools/venv/bin/python menu.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=music-tools

[Install]
WantedBy=multi-user.target
```

#### 5. Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable music-tools

# Start service
sudo systemctl start music-tools

# Check status
sudo systemctl status music-tools

# View logs
sudo journalctl -u music-tools -f
```

### Web Interface (Optional)

If deploying with web interface:

#### Using Nginx

```nginx
# /etc/nginx/sites-available/music-tools
server {
    listen 80;
    server_name music-tools.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SSL configuration (recommended)
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/music-tools.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/music-tools.example.com/privkey.pem;
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/music-tools /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Deploying Additional Applications

**Note:** Additional applications (Tag Editor, EDM Scraper) are not yet migrated to the monorepo structure. This section will be updated when those applications are available for deployment.

For now, only Music Tools is production-ready for deployment in the monorepo structure.

---

## Production Considerations

### Performance Optimization

#### 1. Database Optimization

```python
# Use connection pooling
from music_tools_common.database import DatabaseManager

db = DatabaseManager(
    db_path="/var/lib/music-tools/data/music_tools.db",
    pool_size=10,
    max_overflow=20
)
```

#### 2. Caching Strategy

```bash
# Redis for distributed caching
CACHE_BACKEND=redis
CACHE_REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600
```

#### 3. Rate Limiting

```python
# Implement rate limiting for API calls
from music_tools_common.utils import RateLimiter

rate_limiter = RateLimiter(
    max_calls=100,
    period=60  # 100 calls per minute
)
```

### High Availability

#### 1. Load Balancing

```nginx
upstream music_tools {
    server 192.168.1.10:8000;
    server 192.168.1.11:8000;
    server 192.168.1.12:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://music_tools;
    }
}
```

#### 2. Database Replication

```bash
# Primary database
DATABASE_PRIMARY=postgresql://primary.db.example.com:5432/music_tools

# Read replicas
DATABASE_REPLICAS=postgresql://replica1.db.example.com:5432/music_tools,postgresql://replica2.db.example.com:5432/music_tools
```

#### 3. Health Checks

```python
# /opt/music-tools/healthcheck.py
from music_tools_common.database import get_database
from music_tools_common.config import config_manager

def health_check():
    """Check application health."""
    try:
        # Check database
        db = get_database()
        db.execute("SELECT 1")

        # Check config
        config = config_manager.load_config('spotify')

        return {"status": "healthy", "version": "1.0.0"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Security Hardening

#### 1. File Permissions

```bash
# Configuration files
chmod 600 /etc/music-tools/*.env
chown root:music-tools /etc/music-tools/*.env

# Application directories
chmod 755 /opt/music-tools
chmod 750 /var/lib/music-tools
chmod 750 /var/log/music-tools

# Data files
chmod 600 /var/lib/music-tools/data/*
```

#### 2. Network Security

```bash
# Firewall rules (UFW)
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw deny from any to any port 8000  # Block direct access
sudo ufw enable
```

#### 3. SELinux/AppArmor

```bash
# SELinux context
sudo chcon -R -t httpd_sys_content_t /opt/music-tools
sudo setsebool -P httpd_can_network_connect 1

# AppArmor profile
sudo vim /etc/apparmor.d/music-tools
# Add appropriate rules
sudo apparmor_parser -r /etc/apparmor.d/music-tools
```

### Resource Limits

```ini
# In systemd service file
[Service]
# Memory limits
MemoryMax=2G
MemoryHigh=1.5G

# CPU limits
CPUQuota=200%  # Max 2 CPU cores

# Process limits
LimitNOFILE=4096
LimitNPROC=512

# Timeout limits
TimeoutStartSec=60
TimeoutStopSec=30
```

---

## Monitoring and Logging

### Logging Configuration

#### 1. Structured Logging

```python
# Configure in application
import logging
import logging.handlers

logger = logging.getLogger(__name__)

# JSON formatter
from pythonjsonlogger import jsonlogger

handler = logging.handlers.RotatingFileHandler(
    '/var/log/music-tools/app.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(name)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
```

#### 2. Log Rotation

```bash
# /etc/logrotate.d/music-tools
/var/log/music-tools/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 music-tools music-tools
    sharedscripts
    postrotate
        systemctl reload music-tools > /dev/null 2>&1 || true
    endscript
}
```

### Monitoring Setup

#### 1. Prometheus Metrics

```python
# Add metrics endpoint
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('music_tools_requests_total', 'Total requests')
request_duration = Histogram('music_tools_request_duration_seconds', 'Request duration')

@app.route('/metrics')
def metrics():
    return generate_latest()
```

#### 2. Health Check Endpoint

```python
@app.route('/health')
def health():
    return health_check(), 200
```

#### 3. Monitoring with Grafana

```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'music-tools'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

---

## Backup and Recovery

### Backup Strategy

#### 1. Database Backup

```bash
# /opt/music-tools/backup-db.sh
#!/bin/bash
BACKUP_DIR=/var/backups/music-tools
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup SQLite database
sqlite3 /var/lib/music-tools/data/music_tools.db ".backup '$BACKUP_DIR/music_tools_$DATE.db'"

# Compress
gzip $BACKUP_DIR/music_tools_$DATE.db

# Keep only last 30 days
find $BACKUP_DIR -name "music_tools_*.db.gz" -mtime +30 -delete
```

#### 2. Configuration Backup

```bash
# Backup configuration
tar -czf /var/backups/music-tools/config_$DATE.tar.gz \
  /etc/music-tools \
  /var/lib/music-tools/config
```

#### 3. Automated Backups

```bash
# Crontab
0 1 * * * /opt/music-tools/backup-db.sh >> /var/log/music-tools/backup.log 2>&1
0 2 * * 0 /opt/music-tools/backup-config.sh >> /var/log/music-tools/backup.log 2>&1
```

### Recovery Procedures

#### 1. Database Recovery

```bash
# Stop service
sudo systemctl stop music-tools

# Restore database
gunzip -c /var/backups/music-tools/music_tools_20251115.db.gz > \
  /var/lib/music-tools/data/music_tools.db

# Set permissions
sudo chown music-tools:music-tools /var/lib/music-tools/data/music_tools.db
sudo chmod 600 /var/lib/music-tools/data/music_tools.db

# Start service
sudo systemctl start music-tools
```

#### 2. Full System Recovery

```bash
# Restore from backup
tar -xzf /var/backups/music-tools/full_backup_20251115.tar.gz -C /

# Reinstall dependencies
cd /opt/music-tools
source venv/bin/activate
pip install -e packages/common
pip install -e apps/music-tools

# Restart services
sudo systemctl restart music-tools
```

---

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service status
sudo systemctl status music-tools

# Check logs
sudo journalctl -u music-tools -n 100

# Check permissions
ls -la /opt/music-tools
ls -la /var/lib/music-tools

# Verify environment
sudo -u music-tools env
```

#### Database Errors

```bash
# Check database integrity
sqlite3 /var/lib/music-tools/data/music_tools.db "PRAGMA integrity_check;"

# Rebuild database
sqlite3 /var/lib/music-tools/data/music_tools.db ".dump" | \
  sqlite3 /var/lib/music-tools/data/music_tools_new.db

mv /var/lib/music-tools/data/music_tools.db /var/lib/music-tools/data/music_tools_old.db
mv /var/lib/music-tools/data/music_tools_new.db /var/lib/music-tools/data/music_tools.db
```

#### API Authentication Failures

```bash
# Verify credentials
sudo -u music-tools bash -c 'source /etc/music-tools/music-tools.env && env | grep SPOTIPY'

# Test API access
curl -X GET "https://api.spotify.com/v1/me" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

#### Performance Issues

```bash
# Check resource usage
top -u music-tools
htop -u music-tools

# Check disk I/O
iotop -u music-tools

# Check network
nethogs
```

---

## Additional Resources

- [Development Guide](DEVELOPMENT.md)
- [Monorepo Architecture](../architecture/MONOREPO.md)
- [Security Guide](../../SECURITY.md)
- [API Documentation](../api/)

---

**Last Updated:** 2025-11-15
**Maintained By:** Music Tools Team
**Support:** support@example.com
