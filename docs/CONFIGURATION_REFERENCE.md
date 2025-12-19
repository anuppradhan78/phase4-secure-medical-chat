# Configuration Reference - Secure Medical Chat

This comprehensive reference documents all configuration options, environment variables, and settings for the Secure Medical Chat system.

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Core Configuration](#core-configuration)
3. [Security Settings](#security-settings)
4. [Cost Management](#cost-management)
5. [Performance Settings](#performance-settings)
6. [Database Configuration](#database-configuration)
7. [Logging Configuration](#logging-configuration)
8. [Environment-Specific Settings](#environment-specific-settings)
9. [Validation and Testing](#validation-and-testing)

## Configuration Overview

The Secure Medical Chat system uses environment variables for configuration, loaded from `.env` files or system environment. Configuration is validated at startup and can be adjusted for different deployment scenarios.

### Configuration Hierarchy

1. **System Environment Variables** (highest priority)
2. **Environment-specific .env files** (e.g., `.env.production`)
3. **Default .env file**
4. **Built-in defaults** (lowest priority)

### Configuration Files

- `.env.example` - Template with all available options
- `.env` - Default configuration file
- `.env.development` - Development-specific settings
- `.env.staging` - Staging environment settings
- `.env.production` - Production environment settings

## Core Configuration

### Application Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENVIRONMENT` | string | `development` | Application environment: `development`, `staging`, `production` |
| `DEBUG` | boolean | `false` | Enable debug mode with detailed logging |
| `LOG_LEVEL` | string | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `HOST` | string | `0.0.0.0` | Server host address |
| `PORT` | integer | `8000` | Server port number |
| `WORKERS` | integer | `1` | Number of worker processes (production) |

**Example**:
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
WORKERS=4
```

### LLM Provider Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLM_PROVIDER` | string | `openai` | LLM provider: `openai`, `anthropic`, `azure` |
| `OPENAI_API_KEY` | string | - | OpenAI API key (required) |
| `OPENAI_ORG_ID` | string | - | OpenAI organization ID (optional) |
| `DEFAULT_MODEL` | string | `gpt-3.5-turbo` | Default LLM model |
| `MAX_TOKENS` | integer | `1000` | Maximum tokens per response |
| `TEMPERATURE` | float | `0.7` | LLM temperature (0.0-2.0) |
| `LLM_TIMEOUT` | integer | `30` | LLM request timeout in seconds |

**Example**:
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-your-api-key-here
DEFAULT_MODEL=gpt-4
MAX_TOKENS=1500
TEMPERATURE=0.3
LLM_TIMEOUT=60
```

### Authentication Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `JWT_SECRET_KEY` | string | - | JWT signing secret (required, change in production) |
| `JWT_ALGORITHM` | string | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | integer | `1440` | JWT token expiry in minutes (24 hours) |
| `ENABLE_RBAC` | boolean | `true` | Enable role-based access control |

**Example**:
```bash
JWT_SECRET_KEY=super-secure-production-key-from-vault
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
ENABLE_RBAC=true
```

## Security Settings

### PII/PHI Redaction

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_PII_REDACTION` | boolean | `true` | Enable PII/PHI redaction with Presidio |
| `PRESIDIO_ENTITIES` | string | `PERSON,DATE_TIME,...` | Comma-separated list of entities to detect |
| `PRESIDIO_LOG_LEVEL` | string | `INFO` | Presidio logging level |
| `PRESIDIO_SCORE_THRESHOLD` | float | `0.8` | Minimum confidence score for entity detection |

**Available Presidio Entities**:
- `PERSON` - Names of individuals
- `DATE_TIME` - Dates and times
- `PHONE_NUMBER` - Phone numbers
- `EMAIL_ADDRESS` - Email addresses
- `MEDICAL_LICENSE` - Medical license numbers
- `US_SSN` - Social Security Numbers
- `LOCATION` - Addresses and locations
- `CREDIT_CARD` - Credit card numbers
- `US_PASSPORT` - US Passport numbers
- `US_DRIVER_LICENSE` - Driver's license numbers
- `US_BANK_NUMBER` - Bank account numbers
- `IBAN_CODE` - International bank account numbers
- `IP_ADDRESS` - IP addresses

**Example**:
```bash
ENABLE_PII_REDACTION=true
PRESIDIO_ENTITIES=PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION
PRESIDIO_LOG_LEVEL=INFO
PRESIDIO_SCORE_THRESHOLD=0.85
```

### Guardrails Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_GUARDRAILS` | boolean | `true` | Enable security guardrails |
| `ENABLE_LLAMA_GUARD` | boolean | `true` | Enable Llama-Guard-3 content classification |
| `ENABLE_NEMO_GUARDRAILS` | boolean | `true` | Enable NeMo Guardrails |
| `GUARDRAILS_CONFIG_PATH` | string | `config/guardrails` | Path to guardrails configuration |
| `GUARDRAILS_TIMEOUT` | integer | `10` | Guardrails processing timeout in seconds |

**Example**:
```bash
ENABLE_GUARDRAILS=true
ENABLE_LLAMA_GUARD=true
ENABLE_NEMO_GUARDRAILS=true
GUARDRAILS_CONFIG_PATH=config/guardrails
GUARDRAILS_TIMEOUT=15
```

### Medical Safety Controls

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_MEDICAL_DISCLAIMERS` | boolean | `true` | Automatically add medical disclaimers |
| `ENABLE_EMERGENCY_DETECTION` | boolean | `true` | Detect emergency symptoms and provide 911 guidance |
| `ENABLE_DOSAGE_RESTRICTIONS` | boolean | `true` | Refuse specific medication dosage requests |
| `ENABLE_SOURCE_CITATIONS` | boolean | `true` | Add medical source citations |

**Example**:
```bash
ENABLE_MEDICAL_DISCLAIMERS=true
ENABLE_EMERGENCY_DETECTION=true
ENABLE_DOSAGE_RESTRICTIONS=true
ENABLE_SOURCE_CITATIONS=true
```

### Rate Limiting

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_RATE_LIMITING` | boolean | `true` | Enable rate limiting |
| `PATIENT_MAX_QUERIES_PER_HOUR` | integer | `10` | Rate limit for patient role |
| `PHYSICIAN_MAX_QUERIES_PER_HOUR` | integer | `100` | Rate limit for physician role |
| `ADMIN_MAX_QUERIES_PER_HOUR` | integer | `1000` | Rate limit for admin role |
| `RATE_LIMIT_STORAGE` | string | `memory` | Rate limit storage: `memory`, `redis` |

**Example**:
```bash
ENABLE_RATE_LIMITING=true
PATIENT_MAX_QUERIES_PER_HOUR=15
PHYSICIAN_MAX_QUERIES_PER_HOUR=150
ADMIN_MAX_QUERIES_PER_HOUR=1500
RATE_LIMIT_STORAGE=redis
```

## Cost Management

### Helicone Integration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `HELICONE_API_KEY` | string | - | Helicone API key for cost tracking |
| `ENABLE_COST_TRACKING` | boolean | `true` | Enable cost tracking and analytics |
| `COST_LIMIT_DAILY` | float | `100.0` | Daily cost limit in USD |
| `COST_ALERT_THRESHOLD` | float | `80.0` | Alert threshold as percentage of daily limit |
| `HELICONE_BASE_URL` | string | `https://oai.hconeai.com` | Helicone proxy base URL |

**Example**:
```bash
HELICONE_API_KEY=sk-helicone-your-api-key-here
ENABLE_COST_TRACKING=true
COST_LIMIT_DAILY=500.0
COST_ALERT_THRESHOLD=85.0
```

### Response Caching

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_RESPONSE_CACHE` | boolean | `true` | Enable response caching |
| `CACHE_TTL_HOURS` | integer | `24` | Cache time-to-live in hours |
| `CACHE_MAX_SIZE` | integer | `1000` | Maximum number of cached responses |
| `CACHE_BACKEND` | string | `memory` | Cache backend: `memory`, `redis` |

**Example**:
```bash
ENABLE_RESPONSE_CACHE=true
CACHE_TTL_HOURS=48
CACHE_MAX_SIZE=2000
CACHE_BACKEND=redis
```

### Model Routing

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_MODEL_ROUTING` | boolean | `true` | Enable intelligent model routing |
| `SIMPLE_MODEL` | string | `gpt-3.5-turbo` | Model for simple queries |
| `COMPLEX_MODEL` | string | `gpt-4` | Model for complex queries |
| `COMPLEXITY_THRESHOLD` | float | `0.5` | Threshold for model routing (0.0-1.0) |

**Example**:
```bash
ENABLE_MODEL_ROUTING=true
SIMPLE_MODEL=gpt-3.5-turbo
COMPLEX_MODEL=gpt-4
COMPLEXITY_THRESHOLD=0.6
```

## Performance Settings

### Server Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `UVICORN_WORKERS` | integer | `1` | Number of Uvicorn workers |
| `WORKER_CONNECTIONS` | integer | `1000` | Maximum connections per worker |
| `KEEPALIVE_TIMEOUT` | integer | `5` | Keep-alive timeout in seconds |
| `MAX_REQUEST_SIZE` | integer | `16777216` | Maximum request size in bytes (16MB) |

**Example**:
```bash
UVICORN_WORKERS=4
WORKER_CONNECTIONS=2000
KEEPALIVE_TIMEOUT=10
MAX_REQUEST_SIZE=33554432
```

### Timeout Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REQUEST_TIMEOUT` | integer | `60` | Overall request timeout in seconds |
| `LLM_TIMEOUT` | integer | `30` | LLM API timeout in seconds |
| `PRESIDIO_TIMEOUT` | integer | `10` | PII redaction timeout in seconds |
| `GUARDRAILS_TIMEOUT` | integer | `10` | Guardrails processing timeout in seconds |

**Example**:
```bash
REQUEST_TIMEOUT=120
LLM_TIMEOUT=60
PRESIDIO_TIMEOUT=15
GUARDRAILS_TIMEOUT=15
```

### Streaming Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_STREAMING` | boolean | `true` | Enable streaming responses |
| `STREAM_CHUNK_SIZE` | integer | `1024` | Streaming chunk size in bytes |
| `STREAM_TIMEOUT` | integer | `300` | Streaming timeout in seconds |

**Example**:
```bash
ENABLE_STREAMING=true
STREAM_CHUNK_SIZE=2048
STREAM_TIMEOUT=600
```

## Database Configuration

### Connection Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | string | `sqlite:///./secure_medical_chat.db` | Database connection URL |
| `DATABASE_ECHO` | boolean | `false` | Enable SQL query logging |
| `DATABASE_POOL_SIZE` | integer | `5` | Connection pool size |
| `DATABASE_MAX_OVERFLOW` | integer | `10` | Maximum overflow connections |
| `DATABASE_POOL_TIMEOUT` | integer | `30` | Connection pool timeout in seconds |

**Database URL Examples**:
```bash
# SQLite (development)
DATABASE_URL=sqlite:///./secure_medical_chat.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:password@localhost:5432/medchat

# PostgreSQL with SSL
DATABASE_URL=postgresql://user:password@host:5432/medchat?sslmode=require

# MySQL
DATABASE_URL=mysql://user:password@localhost:3306/medchat
```

### Migration Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AUTO_MIGRATE` | boolean | `true` | Automatically run database migrations |
| `MIGRATION_TIMEOUT` | integer | `300` | Migration timeout in seconds |

**Example**:
```bash
DATABASE_URL=postgresql://medchat:secure_password@localhost:5432/medchat_prod
DATABASE_ECHO=false
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
AUTO_MIGRATE=true
```

## Logging Configuration

### Log Levels and Output

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | string | `INFO` | Global logging level |
| `LOG_FORMAT` | string | `json` | Log format: `json`, `text` |
| `LOG_FILE` | string | `logs/app.log` | Log file path |
| `LOG_MAX_SIZE` | integer | `10485760` | Maximum log file size in bytes (10MB) |
| `LOG_BACKUP_COUNT` | integer | `5` | Number of backup log files |

**Example**:
```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/medchat.log
LOG_MAX_SIZE=52428800
LOG_BACKUP_COUNT=10
```

### Component-Specific Logging

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PRESIDIO_LOG_LEVEL` | string | `INFO` | Presidio component log level |
| `GUARDRAILS_LOG_LEVEL` | string | `INFO` | Guardrails component log level |
| `LLM_LOG_LEVEL` | string | `INFO` | LLM gateway log level |
| `DATABASE_LOG_LEVEL` | string | `WARNING` | Database log level |

**Example**:
```bash
PRESIDIO_LOG_LEVEL=DEBUG
GUARDRAILS_LOG_LEVEL=INFO
LLM_LOG_LEVEL=INFO
DATABASE_LOG_LEVEL=ERROR
```

### Audit Logging

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_AUDIT_LOGGING` | boolean | `true` | Enable comprehensive audit logging |
| `AUDIT_LOG_FILE` | string | `logs/audit.log` | Audit log file path |
| `AUDIT_LOG_RETENTION_DAYS` | integer | `90` | Audit log retention period |
| `LOG_PII_HASHES` | boolean | `true` | Log SHA-256 hashes of PII (not actual PII) |

**Example**:
```bash
ENABLE_AUDIT_LOGGING=true
AUDIT_LOG_FILE=logs/audit.log
AUDIT_LOG_RETENTION_DAYS=365
LOG_PII_HASHES=true
```

## Environment-Specific Settings

### Development Environment

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Relaxed security for testing
ENABLE_LLAMA_GUARD=false
PRESIDIO_ENTITIES=PERSON,EMAIL_ADDRESS,PHONE_NUMBER

# Higher rate limits for testing
PATIENT_MAX_QUERIES_PER_HOUR=50
PHYSICIAN_MAX_QUERIES_PER_HOUR=500

# Lower cost limits
COST_LIMIT_DAILY=50.0

# Shorter cache TTL
CACHE_TTL_HOURS=1

# Local database
DATABASE_URL=sqlite:///./dev_medical_chat.db
```

### Staging Environment

```bash
# .env.staging
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Production-like security
ENABLE_LLAMA_GUARD=true
PRESIDIO_ENTITIES=PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION

# Moderate rate limits
PATIENT_MAX_QUERIES_PER_HOUR=15
PHYSICIAN_MAX_QUERIES_PER_HOUR=150

# Moderate cost limits
COST_LIMIT_DAILY=200.0

# Standard cache TTL
CACHE_TTL_HOURS=12

# Staging database
DATABASE_URL=postgresql://medchat:password@staging-db:5432/medchat_staging
```

### Production Environment

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Maximum security
ENABLE_LLAMA_GUARD=true
PRESIDIO_ENTITIES=PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD,US_PASSPORT,US_DRIVER_LICENSE,US_BANK_NUMBER,IBAN_CODE,IP_ADDRESS

# Conservative rate limits
PATIENT_MAX_QUERIES_PER_HOUR=10
PHYSICIAN_MAX_QUERIES_PER_HOUR=100

# Production cost limits
COST_LIMIT_DAILY=1000.0
COST_ALERT_THRESHOLD=85.0

# Extended cache TTL
CACHE_TTL_HOURS=24

# Production database with connection pooling
DATABASE_URL=postgresql://medchat:secure_password@prod-db:5432/medchat_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Secure JWT settings
JWT_SECRET_KEY=super-secure-production-key-from-vault
JWT_EXPIRE_MINUTES=480

# Performance settings
UVICORN_WORKERS=4
WORKER_CONNECTIONS=2000
```

### High-Security Environment

```bash
# .env.high-security
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=ERROR

# Maximum PII/PHI detection
PRESIDIO_ENTITIES=PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD,US_PASSPORT,US_DRIVER_LICENSE,US_BANK_NUMBER,IBAN_CODE,IP_ADDRESS,CRYPTO
PRESIDIO_SCORE_THRESHOLD=0.7

# No external cost tracking
ENABLE_COST_TRACKING=false

# No response caching
ENABLE_RESPONSE_CACHE=false

# Very restrictive rate limits
PATIENT_MAX_QUERIES_PER_HOUR=5
PHYSICIAN_MAX_QUERIES_PER_HOUR=50
ADMIN_MAX_QUERIES_PER_HOUR=100

# Short JWT expiry
JWT_EXPIRE_MINUTES=240

# Local database only
DATABASE_URL=sqlite:///./secure_facility.db

# Minimal logging
PRESIDIO_LOG_LEVEL=ERROR
GUARDRAILS_LOG_LEVEL=ERROR
LLM_LOG_LEVEL=ERROR
```

## Validation and Testing

### Configuration Validation

The system includes built-in configuration validation:

```python
# src/config_validator.py
def validate_config():
    """Validate configuration settings."""
    errors = []
    warnings = []
    
    # Required variables
    required = ['LLM_PROVIDER', 'OPENAI_API_KEY', 'JWT_SECRET_KEY']
    for var in required:
        if not os.getenv(var):
            errors.append(f"Missing required variable: {var}")
    
    # Production-specific checks
    if os.getenv('ENVIRONMENT') == 'production':
        if os.getenv('DEBUG', '').lower() == 'true':
            warnings.append("DEBUG should be false in production")
        
        if os.getenv('JWT_SECRET_KEY') == 'dev-secret-key':
            errors.append("JWT_SECRET_KEY must be changed in production")
    
    return {'errors': errors, 'warnings': warnings}
```

### Testing Configuration

```bash
# Test configuration
python src/config_validator.py

# Test with specific environment
ENVIRONMENT=production python src/config_validator.py

# Test configuration loading
python -c "from src.config import get_settings; print(get_settings())"
```

### Configuration Examples

Run configuration examples to see different setups:

```bash
# Show all configuration scenarios
python examples/config_examples.py

# Test specific scenario
python examples/config_examples.py --scenario development
python examples/config_examples.py --scenario production
python examples/config_examples.py --scenario high-security
```

### Environment Variable Precedence

1. **System Environment** (highest priority)
2. **Environment-specific .env file** (e.g., `.env.production`)
3. **Default .env file**
4. **Built-in defaults** (lowest priority)

Example:
```bash
# System environment overrides .env file
export OPENAI_API_KEY=sk-system-key
# This takes precedence over OPENAI_API_KEY in .env file
```

### Configuration Best Practices

1. **Security**:
   - Never commit real API keys to version control
   - Use strong, unique JWT secrets in production
   - Enable all security features in production
   - Use environment-specific configurations

2. **Performance**:
   - Adjust worker count based on server resources
   - Enable caching for better performance
   - Set appropriate timeouts
   - Use connection pooling for databases

3. **Cost Management**:
   - Set appropriate daily cost limits
   - Enable cost tracking and alerts
   - Use model routing to optimize costs
   - Monitor usage regularly

4. **Monitoring**:
   - Enable audit logging
   - Set appropriate log levels
   - Use structured logging (JSON) in production
   - Monitor rate limits and usage

5. **Environment Separation**:
   - Use different configurations per environment
   - Test configuration changes in development first
   - Use secure secret management in production
   - Document configuration changes

This configuration reference provides comprehensive documentation for all settings and options available in the Secure Medical Chat system.