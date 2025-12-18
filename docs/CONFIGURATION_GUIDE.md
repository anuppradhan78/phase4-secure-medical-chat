# Configuration Guide - Secure Medical Chat

This guide demonstrates how to configure the Secure Medical Chat system for different environments and use cases using environment variables.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Variables Reference](#environment-variables-reference)
3. [Configuration Scenarios](#configuration-scenarios)
4. [Validation and Testing](#validation-and-testing)
5. [Troubleshooting](#troubleshooting)

## Quick Start

1. **Copy the example configuration:**
   ```bash
   cp .env.example .env
   ```

2. **Set required variables:**
   ```bash
   # Required for basic functionality
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-your-openai-api-key-here
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
   ```

3. **Validate configuration:**
   ```bash
   python src/startup_config.py
   ```

4. **Start the application:**
   ```bash
   python -m src.main
   ```

## Environment Variables Reference

### Core Configuration (Required)

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `LLM_PROVIDER` | LLM provider to use | - | `openai` |
| `OPENAI_API_KEY` | OpenAI API key | - | `sk-proj-...` |
| `JWT_SECRET_KEY` | JWT signing secret | - | `super-secure-key` |

### Application Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENVIRONMENT` | Application environment | `development` | `production` |
| `DEBUG` | Enable debug mode | `false` | `true` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `HOST` | Server host | `0.0.0.0` | `localhost` |
| `PORT` | Server port | `8000` | `8080` |

### Cost Management & Optimization

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `HELICONE_API_KEY` | Helicone proxy API key | - | `sk-helicone-...` |
| `COST_LIMIT_DAILY` | Daily cost limit (USD) | `100.0` | `500.0` |
| `COST_ALERT_THRESHOLD` | Alert threshold (%) | `80.0` | `90.0` |
| `ENABLE_COST_TRACKING` | Enable cost tracking | `true` | `false` |
| `ENABLE_RESPONSE_CACHE` | Enable response caching | `true` | `false` |
| `CACHE_TTL_HOURS` | Cache TTL in hours | `24` | `48` |

### Security & Privacy

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `PRESIDIO_ENTITIES` | PII entities to detect | `PERSON,DATE_TIME,...` | `PERSON,EMAIL_ADDRESS` |
| `ENABLE_PII_REDACTION` | Enable PII redaction | `true` | `false` |
| `ENABLE_GUARDRAILS` | Enable guardrails | `true` | `false` |
| `ENABLE_LLAMA_GUARD` | Enable Llama Guard | `true` | `false` |
| `ENABLE_NEMO_GUARDRAILS` | Enable NeMo Guardrails | `true` | `false` |
| `ENABLE_MEDICAL_DISCLAIMERS` | Add medical disclaimers | `true` | `false` |
| `GUARDRAILS_CONFIG_PATH` | Guardrails config path | `config/guardrails` | `custom/path` |

### Rate Limiting

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENABLE_RATE_LIMITING` | Enable rate limiting | `true` | `false` |
| `PATIENT_MAX_QUERIES_PER_HOUR` | Patient rate limit | `10` | `5` |
| `PHYSICIAN_MAX_QUERIES_PER_HOUR` | Physician rate limit | `100` | `50` |
| `ADMIN_MAX_QUERIES_PER_HOUR` | Admin rate limit | `1000` | `500` |

### LLM Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DEFAULT_MODEL` | Default LLM model | `gpt-3.5-turbo` | `gpt-4` |
| `MAX_TOKENS` | Max tokens per response | `1000` | `2000` |
| `TEMPERATURE` | LLM temperature | `0.7` | `0.1` |
| `LLM_TIMEOUT` | LLM request timeout (s) | `30` | `60` |

### Authentication

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | `RS256` |
| `JWT_EXPIRE_MINUTES` | JWT expiry (minutes) | `1440` | `480` |
| `ENABLE_RBAC` | Enable RBAC | `true` | `false` |

### Database

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATABASE_URL` | Database connection URL | `sqlite:///./secure_medical_chat.db` | `postgresql://...` |
| `DATABASE_ECHO` | Enable SQL logging | `false` | `true` |

## Configuration Scenarios

### 1. Development Environment

**Use Case:** Local development with debugging enabled and relaxed security for testing.

```bash
# .env.development
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

**Benefits:**
- Detailed logging for debugging
- Lower cost limits to prevent unexpected charges
- Relaxed security for easier testing
- Higher rate limits for development workflows

### 2. Production Environment

**Use Case:** Production deployment with maximum security and monitoring.

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

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
DATABASE_URL=postgresql://user:pass@prod-db:5432/medical_chat
```

**Benefits:**
- All security features enabled
- Comprehensive PII/PHI detection
- Cost monitoring with alerts
- Conservative rate limits
- Secure JWT configuration

### 3. High-Security Medical Facility

**Use Case:** Maximum security for sensitive medical environments.

```bash
# .env.high-security
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-secure-facility-key
DEFAULT_MODEL=gpt-4

# Cost Settings (No external tracking)
COST_LIMIT_DAILY=500.0
ENABLE_COST_TRACKING=false
ENABLE_RESPONSE_CACHE=false

# Security (Maximum protection)
PRESIDIO_ENTITIES=PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD,US_PASSPORT,US_DRIVER_LICENSE,US_BANK_NUMBER,IBAN_CODE,IP_ADDRESS
PRESIDIO_LOG_LEVEL=ERROR
ENABLE_PII_REDACTION=true
ENABLE_GUARDRAILS=true
ENABLE_LLAMA_GUARD=true
ENABLE_NEMO_GUARDRAILS=true
ENABLE_MEDICAL_DISCLAIMERS=true

# Authentication
JWT_SECRET_KEY=ultra-secure-facility-key-256-bit
JWT_EXPIRE_MINUTES=240

# Rate Limits (Very restrictive)
PATIENT_MAX_QUERIES_PER_HOUR=5
PHYSICIAN_MAX_QUERIES_PER_HOUR=50
ADMIN_MAX_QUERIES_PER_HOUR=100

# Database (Local only)
DATABASE_URL=sqlite:///./secure_facility.db
```

**Benefits:**
- Maximum PII/PHI entity detection
- No response caching (no data retention)
- Minimal logging to reduce exposure
- Very restrictive rate limits
- Local database only

### 4. Cost-Optimized Setup

**Use Case:** Minimize costs while maintaining essential functionality.

```bash
# .env.cost-optimized
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# LLM Configuration (Cost-optimized)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-cost-optimized-key
DEFAULT_MODEL=gpt-3.5-turbo
MAX_TOKENS=500
TEMPERATURE=0.3
HELICONE_API_KEY=sk-helicone-cost-tracking

# Cost Settings
COST_LIMIT_DAILY=100.0
COST_ALERT_THRESHOLD=70.0
ENABLE_RESPONSE_CACHE=true
CACHE_TTL_HOURS=48

# Security (Essential only)
PRESIDIO_ENTITIES=PERSON,EMAIL_ADDRESS,PHONE_NUMBER,MEDICAL_LICENSE
ENABLE_PII_REDACTION=true
ENABLE_GUARDRAILS=true
ENABLE_LLAMA_GUARD=false
ENABLE_NEMO_GUARDRAILS=true

# Authentication
JWT_SECRET_KEY=cost-optimized-secret-key

# Rate Limits (Slightly lower)
PATIENT_MAX_QUERIES_PER_HOUR=8
PHYSICIAN_MAX_QUERIES_PER_HOUR=80
ADMIN_MAX_QUERIES_PER_HOUR=800

# Database
DATABASE_URL=sqlite:///./cost_optimized.db
```

**Benefits:**
- Use cheaper GPT-3.5-turbo model
- Limit max tokens to reduce costs
- Extended cache TTL for better hit rates
- Disable expensive Llama Guard model
- Essential PII entities only

### 5. Research Environment

**Use Case:** Research and experimentation with flexibility and detailed logging.

```bash
# .env.research
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# LLM Configuration (Best quality)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-research-key
DEFAULT_MODEL=gpt-4
MAX_TOKENS=2000
TEMPERATURE=0.1

# Cost Settings
COST_LIMIT_DAILY=300.0
ENABLE_RESPONSE_CACHE=false

# Security (Flexible for research)
PRESIDIO_ENTITIES=PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,LOCATION
ENABLE_PII_REDACTION=true
ENABLE_GUARDRAILS=false
ENABLE_LLAMA_GUARD=false
ENABLE_NEMO_GUARDRAILS=false
ENABLE_MEDICAL_DISCLAIMERS=false

# Authentication
JWT_SECRET_KEY=research-environment-key
JWT_EXPIRE_MINUTES=1440

# Rate Limits (High for testing)
PATIENT_MAX_QUERIES_PER_HOUR=100
PHYSICIAN_MAX_QUERIES_PER_HOUR=500
ADMIN_MAX_QUERIES_PER_HOUR=1000

# Database
DATABASE_URL=sqlite:///./research_data.db
```

**Benefits:**
- GPT-4 for highest quality responses
- No response caching for fresh data
- Guardrails disabled for flexibility
- High rate limits for extensive testing
- Long JWT expiry for research sessions

## Validation and Testing

### 1. Configuration Validation

Run the configuration validator to test different scenarios:

```bash
python src/config_validator.py
```

This will test:
- Minimal configuration
- Full configuration with all options
- Production-specific requirements
- Invalid configuration handling
- Missing required variables
- Different guardrail settings
- Cost limit variations
- Security feature toggles

### 2. Startup Validation

Validate your current configuration:

```bash
python src/startup_config.py
```

This checks:
- Required files and directories
- API key configuration
- Security settings
- Cost settings
- Database settings
- Environment-specific requirements

### 3. Configuration Examples

Run configuration examples to see different setups:

```bash
python examples/config_examples.py
```

### 4. Test Configuration

Test your configuration with the test script:

```bash
python test_configuration.py
```

### 5. Runtime Configuration Check

Check configuration via API (when app is running):

```bash
curl http://localhost:8000/api/config
```

## Troubleshooting

### Common Issues

#### 1. Configuration Not Loading

**Error:** `Required environment variable LLM_PROVIDER is not set`

**Solution:**
```bash
# Check if .env file exists
ls -la .env

# Copy from example if needed
cp .env.example .env

# Edit .env file with your values
nano .env
```

#### 2. Invalid LLM Provider

**Error:** `Invalid LLM_PROVIDER 'invalid_provider'`

**Solution:**
```bash
# Set to valid provider
LLM_PROVIDER=openai
```

Valid providers: `openai`, `anthropic`, `azure`

#### 3. JWT Secret in Production

**Error:** `JWT_SECRET_KEY must be changed from default value in production`

**Solution:**
```bash
# Generate secure key for production
JWT_SECRET_KEY=your-super-secure-production-key-from-vault
```

#### 4. API Key Format Issues

**Error:** `OPENAI_API_KEY format may be incorrect`

**Solution:**
```bash
# Ensure key starts with 'sk-'
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

#### 5. Guardrails Config Missing

**Warning:** `Guardrails config directory not found`

**Solution:**
```bash
# Create guardrails directory
mkdir -p config/guardrails

# Or disable guardrails
ENABLE_GUARDRAILS=false
```

#### 6. Database Connection Issues

**Error:** `Cannot create database directory`

**Solution:**
```bash
# Create database directory
mkdir -p data

# Or use different path
DATABASE_URL=sqlite:///./custom_path/database.db
```

### Configuration Debugging

#### 1. Enable Debug Logging

```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

#### 2. Check Configuration Summary

```bash
# Via API
curl http://localhost:8000/api/config

# Via startup script
python src/startup_config.py
```

#### 3. Validate Specific Scenarios

```bash
# Test with minimal config
LLM_PROVIDER=openai OPENAI_API_KEY=sk-test JWT_SECRET_KEY=test python src/config_validator.py
```

### Environment-Specific Tips

#### Development
- Use `DEBUG=true` for detailed logging
- Set lower cost limits (`COST_LIMIT_DAILY=50.0`)
- Use shorter cache TTL (`CACHE_TTL_HOURS=1`)
- Enable higher rate limits for testing

#### Production
- Use `DEBUG=false` and `LOG_LEVEL=INFO`
- Set secure JWT secret from vault
- Enable all security features
- Use conservative rate limits
- Enable cost monitoring

#### High Security
- Minimize logging (`LOG_LEVEL=WARNING`)
- Disable caching (`ENABLE_RESPONSE_CACHE=false`)
- Use maximum PII entity detection
- Very restrictive rate limits
- Local database only

## Configuration Best Practices

1. **Security First**
   - Always change default JWT secret in production
   - Use environment-specific API keys
   - Enable all security features in production
   - Regularly rotate secrets

2. **Cost Management**
   - Set appropriate daily limits
   - Enable cost alerts
   - Use caching to reduce API calls
   - Choose models based on use case

3. **Environment Separation**
   - Use different .env files per environment
   - Never commit .env files to version control
   - Use secure secret management in production
   - Test configuration changes in development first

4. **Monitoring**
   - Enable appropriate logging levels
   - Monitor cost usage regularly
   - Set up alerts for security events
   - Track rate limit usage

5. **Performance**
   - Enable response caching where appropriate
   - Choose optimal cache TTL values
   - Use appropriate model selection
   - Monitor latency metrics

This configuration system provides flexibility while maintaining security and cost control. Choose the scenario that best fits your use case and customize as needed.