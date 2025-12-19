# Deployment Guide - Secure Medical Chat

This comprehensive guide covers deployment scenarios, environment setup, configuration management, and production best practices for the Secure Medical Chat system.

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Environment Setup](#environment-setup)
3. [Local Development](#local-development)
4. [Production Deployment](#production-deployment)
5. [Cloud Deployment](#cloud-deployment)
6. [Container Deployment](#container-deployment)
7. [Configuration Management](#configuration-management)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)

## Deployment Overview

The Secure Medical Chat system supports multiple deployment scenarios:

- **Local Development**: Single-machine setup for development and testing
- **Production Server**: Traditional server deployment with full security
- **Cloud Deployment**: AWS, Azure, or GCP deployment with managed services
- **Container Deployment**: Docker and Kubernetes deployment
- **Hybrid Deployment**: On-premises with cloud services integration

### Architecture Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │   Web Server    │    │   Application   │
│                 │    │                 │    │                 │
│ - SSL/TLS       │───▶│ - Nginx/Apache  │───▶│ - FastAPI       │
│ - Rate Limiting │    │ - Static Files  │    │ - Security      │
│ - DDoS Protection│    │ - Compression   │    │ - Business Logic│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Database     │    │   External APIs │    │   Monitoring    │
│                 │    │                 │    │                 │
│ - PostgreSQL    │    │ - OpenAI        │    │ - Logs          │
│ - Redis Cache   │    │ - Helicone      │    │ - Metrics       │
│ - Backups       │    │ - Presidio      │    │ - Alerts        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Environment Setup

### System Requirements

#### Minimum Requirements
- **CPU**: 2 cores, 2.4 GHz
- **RAM**: 4 GB
- **Storage**: 20 GB SSD
- **Network**: 100 Mbps
- **OS**: Ubuntu 20.04+, CentOS 8+, or Windows Server 2019+

#### Recommended Requirements
- **CPU**: 4 cores, 3.0 GHz
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **Network**: 1 Gbps
- **OS**: Ubuntu 22.04 LTS

#### Production Requirements
- **CPU**: 8+ cores, 3.2 GHz
- **RAM**: 16+ GB
- **Storage**: 100+ GB SSD (with backup)
- **Network**: 10 Gbps
- **OS**: Ubuntu 22.04 LTS or RHEL 9

### Software Dependencies

#### Core Dependencies
```bash
# Python 3.9+ (3.10+ recommended)
python3 --version

# Package manager
pip --version

# Git for version control
git --version

# SSL/TLS certificates
openssl version
```

#### Optional Dependencies
```bash
# Docker (for containerized deployment)
docker --version

# Nginx (for reverse proxy)
nginx -v

# PostgreSQL (for production database)
psql --version

# Redis (for caching and sessions)
redis-cli --version
```

## Local Development

### Quick Setup

1. **Clone Repository**:
   ```bash
   git clone <repository-url>
   cd phase4-secure-medical-chat
   ```

2. **Create Virtual Environment**:
   ```bash
   # Use venv (NOT conda/anaconda)
   python3 -m venv venv
   
   # Activate environment
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize Database**:
   ```bash
   python -c "from src.database import init_database; init_database()"
   ```

6. **Start Development Server**:
   ```bash
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Development Configuration

Create a development-specific `.env.development`:

```bash
# Development Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-dev-key
DEFAULT_MODEL=gpt-3.5-turbo
MAX_TOKENS=1000

# Cost Settings (Lower limits for dev)
COST_LIMIT_DAILY=50.0
ENABLE_RESPONSE_CACHE=true
CACHE_TTL_HOURS=1

# Security (Relaxed for testing)
PRESIDIO_ENTITIES=PERSON,EMAIL_ADDRESS,PHONE_NUMBER
ENABLE_PII_REDACTION=true
ENABLE_GUARDRAILS=true
ENABLE_LLAMA_GUARD=false
ENABLE_NEMO_GUARDRAILS=true

# Authentication
JWT_SECRET_KEY=dev-secret-key-not-for-production
JWT_EXPIRE_MINUTES=60

# Rate Limits (Higher for testing)
PATIENT_MAX_QUERIES_PER_HOUR=20
PHYSICIAN_MAX_QUERIES_PER_HOUR=200
ADMIN_MAX_QUERIES_PER_HOUR=2000

# Database
DATABASE_URL=sqlite:///./dev_medical_chat.db
```

### Development Tools

#### Code Quality
```bash
# Code formatting
black src/ tests/

# Linting
flake8 src/ tests/

# Type checking
mypy src/

# Security scanning
bandit -r src/
```

#### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run security tests
pytest tests/security/

# Run integration tests
pytest tests/integration/
```

## Production Deployment

### Pre-Deployment Checklist

- [ ] Server meets minimum requirements
- [ ] SSL/TLS certificates obtained
- [ ] Database configured and secured
- [ ] Environment variables configured
- [ ] Security settings validated
- [ ] Backup procedures established
- [ ] Monitoring configured
- [ ] Load balancer configured (if applicable)

### Server Setup

#### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx postgresql redis-server

# Create application user
sudo useradd -m -s /bin/bash medchat
sudo usermod -aG sudo medchat

# Create application directory
sudo mkdir -p /opt/medchat
sudo chown medchat:medchat /opt/medchat
```

#### 2. Application Deployment

```bash
# Switch to application user
sudo su - medchat

# Clone application
cd /opt/medchat
git clone <repository-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install production dependencies
pip install gunicorn psycopg2-binary
```

#### 3. Database Setup

```bash
# PostgreSQL setup
sudo -u postgres createuser medchat
sudo -u postgres createdb medchat_prod -O medchat
sudo -u postgres psql -c "ALTER USER medchat PASSWORD 'secure_password';"

# Initialize database
cd /opt/medchat
source venv/bin/activate
python -c "from src.database import init_database; init_database()"
```

#### 4. Configuration

Create production configuration `/opt/medchat/.env.production`:

```bash
# Production Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=127.0.0.1
PORT=8000

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-production-key
DEFAULT_MODEL=gpt-4
HELICONE_API_KEY=sk-helicone-production-key

# Cost Settings
COST_LIMIT_DAILY=1000.0
COST_ALERT_THRESHOLD=85.0
ENABLE_COST_TRACKING=true
ENABLE_RESPONSE_CACHE=true
CACHE_TTL_HOURS=24

# Security (Maximum protection)
PRESIDIO_ENTITIES=PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD,US_PASSPORT
ENABLE_PII_REDACTION=true
ENABLE_GUARDRAILS=true
ENABLE_LLAMA_GUARD=true
ENABLE_NEMO_GUARDRAILS=true
ENABLE_MEDICAL_DISCLAIMERS=true

# Authentication
JWT_SECRET_KEY=super-secure-production-key-from-vault
JWT_EXPIRE_MINUTES=480

# Rate Limits (Conservative)
PATIENT_MAX_QUERIES_PER_HOUR=10
PHYSICIAN_MAX_QUERIES_PER_HOUR=100
ADMIN_MAX_QUERIES_PER_HOUR=1000

# Database
DATABASE_URL=postgresql://medchat:secure_password@localhost:5432/medchat_prod
```

#### 5. Systemd Service

Create `/etc/systemd/system/medchat.service`:

```ini
[Unit]
Description=Secure Medical Chat API
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=medchat
Group=medchat
WorkingDirectory=/opt/medchat
Environment=PATH=/opt/medchat/venv/bin
EnvironmentFile=/opt/medchat/.env.production
ExecStart=/opt/medchat/venv/bin/gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable medchat
sudo systemctl start medchat
sudo systemctl status medchat
```

#### 6. Nginx Configuration

Create `/etc/nginx/sites-available/medchat`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';";

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Proxy Configuration
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
    }

    # Static files (if any)
    location /static/ {
        alias /opt/medchat/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/medchat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Cloud Deployment

### AWS Deployment

#### Architecture Overview

```
Internet Gateway
       │
   ALB (Application Load Balancer)
       │
┌──────┴──────┐
│   ECS/EC2   │  ←→  RDS (PostgreSQL)
│  Auto Scaling│  ←→  ElastiCache (Redis)
│   Group      │  ←→  S3 (Logs/Backups)
└─────────────┘  ←→  CloudWatch (Monitoring)
```

#### 1. Infrastructure Setup

**VPC and Networking**:
```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# Create subnets
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id vpc-xxx --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create security groups
aws ec2 create-security-group --group-name medchat-web --description "Web tier security group"
aws ec2 create-security-group --group-name medchat-db --description "Database tier security group"
```

**RDS Database**:
```bash
# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier medchat-prod \
    --db-instance-class db.t3.medium \
    --engine postgres \
    --master-username medchat \
    --master-user-password SecurePassword123! \
    --allocated-storage 100 \
    --vpc-security-group-ids sg-xxx \
    --db-subnet-group-name medchat-subnet-group \
    --backup-retention-period 7 \
    --multi-az \
    --storage-encrypted
```

**ElastiCache Redis**:
```bash
# Create Redis cluster
aws elasticache create-cache-cluster \
    --cache-cluster-id medchat-redis \
    --cache-node-type cache.t3.micro \
    --engine redis \
    --num-cache-nodes 1 \
    --security-group-ids sg-xxx \
    --cache-subnet-group-name medchat-cache-subnet
```

#### 2. Application Deployment

**ECS Task Definition**:
```json
{
  "family": "medchat-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "medchat-app",
      "image": "your-account.dkr.ecr.region.amazonaws.com/medchat:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:medchat/openai-key"
        },
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:medchat/database-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/medchat",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

**ECS Service**:
```bash
# Create ECS service
aws ecs create-service \
    --cluster medchat-cluster \
    --service-name medchat-service \
    --task-definition medchat-task:1 \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:region:account:targetgroup/medchat-tg,containerName=medchat-app,containerPort=8000
```

#### 3. Secrets Management

```bash
# Store API keys in AWS Secrets Manager
aws secretsmanager create-secret \
    --name medchat/openai-key \
    --description "OpenAI API key for Medical Chat" \
    --secret-string "sk-your-openai-key"

aws secretsmanager create-secret \
    --name medchat/jwt-secret \
    --description "JWT secret key for Medical Chat" \
    --secret-string "super-secure-jwt-secret"

aws secretsmanager create-secret \
    --name medchat/database-url \
    --description "Database connection URL" \
    --secret-string "postgresql://medchat:password@rds-endpoint:5432/medchat"
```

### Azure Deployment

#### Architecture Overview

```
Azure Front Door
       │
   App Service
       │
┌──────┴──────┐
│  Web App    │  ←→  Azure Database for PostgreSQL
│  (Linux)    │  ←→  Azure Cache for Redis
│             │  ←→  Azure Storage (Logs)
└─────────────┘  ←→  Application Insights
```

#### 1. Resource Group Setup

```bash
# Create resource group
az group create --name medchat-rg --location eastus

# Create App Service Plan
az appservice plan create \
    --name medchat-plan \
    --resource-group medchat-rg \
    --sku P1V2 \
    --is-linux

# Create Web App
az webapp create \
    --name medchat-app \
    --resource-group medchat-rg \
    --plan medchat-plan \
    --runtime "PYTHON|3.10"
```

#### 2. Database Setup

```bash
# Create PostgreSQL server
az postgres server create \
    --name medchat-db-server \
    --resource-group medchat-rg \
    --location eastus \
    --admin-user medchat \
    --admin-password SecurePassword123! \
    --sku-name GP_Gen5_2 \
    --version 13

# Create database
az postgres db create \
    --name medchat \
    --resource-group medchat-rg \
    --server-name medchat-db-server
```

#### 3. Application Configuration

```bash
# Configure app settings
az webapp config appsettings set \
    --name medchat-app \
    --resource-group medchat-rg \
    --settings \
        ENVIRONMENT=production \
        DEBUG=false \
        LOG_LEVEL=INFO

# Configure connection strings
az webapp config connection-string set \
    --name medchat-app \
    --resource-group medchat-rg \
    --connection-string-type PostgreSQL \
    --settings DATABASE_URL="postgresql://medchat:SecurePassword123!@medchat-db-server.postgres.database.azure.com:5432/medchat"
```

### Google Cloud Platform (GCP) Deployment

#### Architecture Overview

```
Cloud Load Balancer
       │
   Cloud Run
       │
┌──────┴──────┐
│  Container  │  ←→  Cloud SQL (PostgreSQL)
│  Instance   │  ←→  Memorystore (Redis)
│             │  ←→  Cloud Storage
└─────────────┘  ←→  Cloud Monitoring
```

#### 1. Project Setup

```bash
# Set project
gcloud config set project your-project-id

# Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable sql-component.googleapis.com
gcloud services enable redis.googleapis.com
```

#### 2. Database Setup

```bash
# Create Cloud SQL instance
gcloud sql instances create medchat-db \
    --database-version=POSTGRES_13 \
    --tier=db-f1-micro \
    --region=us-central1

# Create database
gcloud sql databases create medchat --instance=medchat-db

# Create user
gcloud sql users create medchat \
    --instance=medchat-db \
    --password=SecurePassword123!
```

#### 3. Deploy to Cloud Run

```bash
# Build and push container
gcloud builds submit --tag gcr.io/your-project-id/medchat

# Deploy to Cloud Run
gcloud run deploy medchat \
    --image gcr.io/your-project-id/medchat \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars ENVIRONMENT=production \
    --set-env-vars DEBUG=false
```

## Container Deployment

### Docker Setup

#### 1. Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create non-root user
RUN useradd --create-home --shell /bin/bash medchat
RUN chown -R medchat:medchat /app
USER medchat

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://medchat:password@db:5432/medchat
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=medchat
      - POSTGRES_USER=medchat
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U medchat"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
```

#### 3. Build and Deploy

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app
```

### Kubernetes Deployment

#### 1. Namespace and ConfigMap

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: medchat

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: medchat-config
  namespace: medchat
data:
  ENVIRONMENT: "production"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  HOST: "0.0.0.0"
  PORT: "8000"
```

#### 2. Secrets

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: medchat-secrets
  namespace: medchat
type: Opaque
data:
  OPENAI_API_KEY: <base64-encoded-key>
  JWT_SECRET_KEY: <base64-encoded-secret>
  DATABASE_URL: <base64-encoded-url>
```

#### 3. Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: medchat-app
  namespace: medchat
spec:
  replicas: 3
  selector:
    matchLabels:
      app: medchat-app
  template:
    metadata:
      labels:
        app: medchat-app
    spec:
      containers:
      - name: medchat
        image: your-registry/medchat:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: medchat-config
        - secretRef:
            name: medchat-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### 4. Service and Ingress

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: medchat-service
  namespace: medchat
spec:
  selector:
    app: medchat-app
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: medchat-ingress
  namespace: medchat
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "10"
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: medchat-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: medchat-service
            port:
              number: 80
```

#### 5. Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Check deployment
kubectl get pods -n medchat
kubectl get services -n medchat
kubectl get ingress -n medchat

# View logs
kubectl logs -f deployment/medchat-app -n medchat
```

## Configuration Management

### Environment-Specific Configuration

#### Development
```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
COST_LIMIT_DAILY=50.0
ENABLE_LLAMA_GUARD=false
PATIENT_MAX_QUERIES_PER_HOUR=20
```

#### Staging
```bash
# .env.staging
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
COST_LIMIT_DAILY=200.0
ENABLE_LLAMA_GUARD=true
PATIENT_MAX_QUERIES_PER_HOUR=15
```

#### Production
```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
COST_LIMIT_DAILY=1000.0
ENABLE_LLAMA_GUARD=true
PATIENT_MAX_QUERIES_PER_HOUR=10
```

### Configuration Validation

Create a configuration validation script:

```python
# scripts/validate_config.py
import os
import sys
from typing import Dict, List

def validate_config() -> Dict[str, List[str]]:
    """Validate configuration for deployment."""
    errors = []
    warnings = []
    
    # Required variables
    required_vars = [
        'LLM_PROVIDER', 'OPENAI_API_KEY', 'JWT_SECRET_KEY'
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")
    
    # Production-specific checks
    if os.getenv('ENVIRONMENT') == 'production':
        if os.getenv('DEBUG', '').lower() == 'true':
            warnings.append("DEBUG should be false in production")
        
        if os.getenv('JWT_SECRET_KEY') == 'dev-secret-key-not-for-production':
            errors.append("JWT_SECRET_KEY must be changed from default in production")
    
    return {'errors': errors, 'warnings': warnings}

if __name__ == '__main__':
    result = validate_config()
    
    if result['warnings']:
        print("WARNINGS:")
        for warning in result['warnings']:
            print(f"  - {warning}")
    
    if result['errors']:
        print("ERRORS:")
        for error in result['errors']:
            print(f"  - {error}")
        sys.exit(1)
    
    print("Configuration validation passed!")
```

## Monitoring and Maintenance

### Health Monitoring

#### Application Health Checks

```python
# src/health.py
from fastapi import APIRouter
from datetime import datetime
import psutil
import asyncio

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        # Check database connectivity
        db_status = await check_database()
        
        # Check external services
        openai_status = await check_openai()
        helicone_status = await check_helicone()
        
        # Check system resources
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        status = "healthy"
        if cpu_usage > 90 or memory_usage > 90 or disk_usage > 90:
            status = "degraded"
        
        if not db_status or not openai_status:
            status = "unhealthy"
        
        return {
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "components": {
                "database": "healthy" if db_status else "unhealthy",
                "openai": "healthy" if openai_status else "unhealthy",
                "helicone": "healthy" if helicone_status else "degraded"
            },
            "system": {
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory_usage,
                "disk_usage_percent": disk_usage
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
```

#### Monitoring Setup

**Prometheus Configuration**:
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'medchat'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

**Grafana Dashboard**:
```json
{
  "dashboard": {
    "title": "Medical Chat Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
          }
        ]
      }
    ]
  }
}
```

### Backup and Recovery

#### Database Backup

```bash
#!/bin/bash
# scripts/backup_database.sh

BACKUP_DIR="/opt/backups/medchat"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="medchat_backup_${TIMESTAMP}.sql"

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform backup
pg_dump -h localhost -U medchat -d medchat_prod > $BACKUP_DIR/$BACKUP_FILE

# Compress backup
gzip $BACKUP_DIR/$BACKUP_FILE

# Upload to cloud storage (optional)
aws s3 cp $BACKUP_DIR/$BACKUP_FILE.gz s3://medchat-backups/

# Clean up old backups (keep last 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

#### Application Backup

```bash
#!/bin/bash
# scripts/backup_application.sh

BACKUP_DIR="/opt/backups/medchat"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/medchat"

# Create backup
tar -czf $BACKUP_DIR/app_backup_${TIMESTAMP}.tar.gz \
    -C $APP_DIR \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude=*.log \
    .

echo "Application backup completed: app_backup_${TIMESTAMP}.tar.gz"
```

### Log Management

#### Log Rotation

```bash
# /etc/logrotate.d/medchat
/opt/medchat/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 medchat medchat
    postrotate
        systemctl reload medchat
    endscript
}
```

#### Centralized Logging

**ELK Stack Configuration**:
```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.15.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:7.15.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: docker.elastic.co/kibana/kibana:7.15.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200

volumes:
  elasticsearch_data:
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

**Symptoms**: Service fails to start, connection errors

**Diagnosis**:
```bash
# Check service status
systemctl status medchat

# Check logs
journalctl -u medchat -f

# Check configuration
python src/startup_config.py

# Check dependencies
pip check
```

**Solutions**:
- Verify environment variables
- Check database connectivity
- Ensure all dependencies are installed
- Validate configuration syntax

#### 2. High Memory Usage

**Symptoms**: Out of memory errors, slow responses

**Diagnosis**:
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Check application memory
docker stats  # if using Docker
```

**Solutions**:
- Increase server memory
- Optimize database queries
- Implement response caching
- Tune garbage collection

#### 3. Database Connection Issues

**Symptoms**: Database connection errors, timeouts

**Diagnosis**:
```bash
# Test database connectivity
psql -h localhost -U medchat -d medchat_prod

# Check database logs
tail -f /var/log/postgresql/postgresql-13-main.log

# Check connection pool
netstat -an | grep :5432
```

**Solutions**:
- Verify database credentials
- Check network connectivity
- Increase connection pool size
- Optimize database configuration

#### 4. SSL/TLS Issues

**Symptoms**: Certificate errors, HTTPS not working

**Diagnosis**:
```bash
# Check certificate validity
openssl x509 -in /path/to/cert.crt -text -noout

# Test SSL connection
openssl s_client -connect your-domain.com:443

# Check Nginx configuration
nginx -t
```

**Solutions**:
- Renew SSL certificates
- Update certificate paths
- Check certificate chain
- Verify domain configuration

### Performance Optimization

#### 1. Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_user_role ON audit_logs(user_role);
CREATE INDEX idx_security_events_threat_type ON security_events(threat_type);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM audit_logs WHERE timestamp > NOW() - INTERVAL '1 day';
```

#### 2. Application Optimization

```python
# Connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

# Response caching
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_response(query_hash: str):
    return cache.get(query_hash)
```

#### 3. Infrastructure Optimization

```bash
# Nginx optimization
worker_processes auto;
worker_connections 1024;

# Enable gzip compression
gzip on;
gzip_types text/plain application/json application/javascript text/css;

# Enable HTTP/2
listen 443 ssl http2;
```

### Disaster Recovery

#### Recovery Procedures

1. **Database Recovery**:
   ```bash
   # Stop application
   systemctl stop medchat
   
   # Restore database
   gunzip -c backup_file.sql.gz | psql -h localhost -U medchat -d medchat_prod
   
   # Start application
   systemctl start medchat
   ```

2. **Application Recovery**:
   ```bash
   # Restore application files
   tar -xzf app_backup.tar.gz -C /opt/medchat/
   
   # Restore configuration
   cp .env.production.backup .env.production
   
   # Restart services
   systemctl restart medchat nginx
   ```

3. **Full System Recovery**:
   ```bash
   # Restore from cloud backup
   aws s3 sync s3://medchat-backups/latest/ /opt/medchat/
   
   # Restore database
   aws s3 cp s3://medchat-backups/latest/database.sql.gz - | gunzip | psql
   
   # Update DNS if needed
   # Verify all services
   ```

This comprehensive deployment guide provides detailed instructions for deploying the Secure Medical Chat system across various environments and platforms, ensuring security, scalability, and maintainability.