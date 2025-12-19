# Troubleshooting Guide - Secure Medical Chat

This comprehensive troubleshooting guide helps diagnose and resolve common issues with the Secure Medical Chat system.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation Issues](#installation-issues)
3. [Configuration Problems](#configuration-problems)
4. [Runtime Errors](#runtime-errors)
5. [Performance Issues](#performance-issues)
6. [Security Issues](#security-issues)
7. [Database Problems](#database-problems)
8. [API Integration Issues](#api-integration-issues)
9. [Deployment Issues](#deployment-issues)
10. [Getting Help](#getting-help)

## Quick Diagnostics

### System Health Check

Run this quick diagnostic script to identify common issues:

```bash
#!/bin/bash
# scripts/quick_diagnostic.sh

echo "=== Secure Medical Chat - Quick Diagnostics ==="
echo

# Check Python version
echo "1. Python Version:"
python --version
echo

# Check if virtual environment is activated
echo "2. Virtual Environment:"
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✓ Virtual environment activated: $VIRTUAL_ENV"
else
    echo "✗ Virtual environment NOT activated"
    echo "  Run: source venv/bin/activate"
fi
echo

# Check required packages
echo "3. Required Packages:"
python -c "import presidio_analyzer, nemoguardrails, openai, fastapi" 2>/dev/null && echo "✓ All packages installed" || echo "✗ Missing packages - run: pip install -r requirements.txt"
echo

# Check environment file
echo "4. Environment Configuration:"
if [ -f ".env" ]; then
    echo "✓ .env file exists"
    # Check for required variables
    grep -q "OPENAI_API_KEY" .env && echo "  ✓ OPENAI_API_KEY configured" || echo "  ✗ OPENAI_API_KEY missing"
    grep -q "JWT_SECRET_KEY" .env && echo "  ✓ JWT_SECRET_KEY configured" || echo "  ✗ JWT_SECRET_KEY missing"
else
    echo "✗ .env file not found"
    echo "  Run: cp .env.example .env"
fi
echo

# Check database
echo "5. Database:"
if [ -f "data/secure_medical_chat.db" ]; then
    echo "✓ Database file exists"
else
    echo "✗ Database not initialized"
    echo "  Run: python -c 'from src.database import init_database; init_database()'"
fi
echo

# Check API server
echo "6. API Server:"
curl -s http://localhost:8000/health > /dev/null 2>&1 && echo "✓ API server is running" || echo "✗ API server not running"
echo

echo "=== Diagnostic Complete ==="
```

### Configuration Validator

```bash
# Validate configuration
python src/startup_config.py

# Expected output:
# ✓ Configuration validation passed
# ✓ All required environment variables set
# ✓ Database connection successful
# ✓ External services accessible
```

## Installation Issues

### Issue: Package Installation Fails

**Symptoms**:
```
ERROR: Could not find a version that satisfies the requirement presidio-analyzer
ERROR: No matching distribution found for presidio-analyzer
```

**Diagnosis**:
```bash
# Check Python version
python --version  # Should be 3.9+

# Check pip version
pip --version

# Check internet connectivity
ping pypi.org
```

**Solutions**:

1. **Upgrade pip**:
   ```bash
   python -m pip install --upgrade pip
   ```

2. **Install with specific Python version**:
   ```bash
   python3.10 -m pip install -r requirements.txt
   ```

3. **Install packages individually**:
   ```bash
   pip install presidio-analyzer presidio-anonymizer
   pip install nemoguardrails
   pip install openai helicone
   pip install fastapi uvicorn
   ```

4. **Use alternative package index**:
   ```bash
   pip install -r requirements.txt --index-url https://pypi.org/simple
   ```

### Issue: Virtual Environment Problems

**Symptoms**:
```
Command 'python' not found
ModuleNotFoundError: No module named 'presidio_analyzer'
```

**Diagnosis**:
```bash
# Check if venv is activated
echo $VIRTUAL_ENV

# Check Python path
which python
```

**Solutions**:

1. **Create new virtual environment**:
   ```bash
   # Remove old venv
   rm -rf venv
   
   # Create new venv
   python3 -m venv venv
   
   # Activate
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Fix activation issues (Windows)**:
   ```powershell
   # If activation is blocked by execution policy
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   venv\Scripts\activate
   ```

### Issue: Spacy Model Missing

**Symptoms**:
```
OSError: [E050] Can't find model 'en_core_web_sm'
```

**Solution**:
```bash
# Download spacy model
python -m spacy download en_core_web_sm

# Or install directly
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.0/en_core_web_sm-3.7.0-py3-none-any.whl
```

## Configuration Problems

### Issue: Missing Environment Variables

**Symptoms**:
```
ValueError: Required environment variable LLM_PROVIDER is not set
KeyError: 'OPENAI_API_KEY'
```

**Diagnosis**:
```bash
# Check if .env file exists
ls -la .env

# Check environment variables
env | grep OPENAI
env | grep JWT_SECRET
```

**Solutions**:

1. **Create .env file**:
   ```bash
   cp .env.example .env
   # Edit .env with your values
   ```

2. **Set required variables**:
   ```bash
   # Add to .env file
   LLM_PROVIDER=openai
   OPENAI_API_KEY=sk-your-api-key-here
   JWT_SECRET_KEY=your-secure-secret-key
   ```

3. **Load environment variables**:
   ```bash
   # Export manually (temporary)
   export OPENAI_API_KEY=sk-your-key
   export JWT_SECRET_KEY=your-secret
   
   # Or use dotenv
   python -c "from dotenv import load_dotenv; load_dotenv()"
   ```

### Issue: Invalid API Keys

**Symptoms**:
```
openai.error.AuthenticationError: Incorrect API key provided
401 Unauthorized
```

**Diagnosis**:
```bash
# Check API key format
echo $OPENAI_API_KEY | head -c 10
# Should start with "sk-"

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Solutions**:

1. **Verify API key**:
   - Log in to OpenAI dashboard
   - Generate new API key
   - Update .env file

2. **Check key format**:
   ```bash
   # OpenAI keys start with "sk-"
   OPENAI_API_KEY=sk-proj-...
   
   # Helicone keys start with "sk-helicone-"
   HELICONE_API_KEY=sk-helicone-...
   ```

3. **Test with curl**:
   ```bash
   curl https://api.openai.com/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [{"role": "user", "content": "Hello"}]
     }'
   ```

### Issue: Configuration Validation Fails

**Symptoms**:
```
ConfigurationError: JWT_SECRET_KEY must be changed from default value in production
ValidationError: Invalid configuration for PRESIDIO_ENTITIES
```

**Diagnosis**:
```bash
# Run configuration validator
python src/config_validator.py

# Check specific settings
python -c "from src.config import get_settings; print(get_settings())"
```

**Solutions**:

1. **Update JWT secret**:
   ```bash
   # Generate secure secret
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # Add to .env
   JWT_SECRET_KEY=<generated-secret>
   ```

2. **Fix Presidio entities**:
   ```bash
   # Correct format (comma-separated, no spaces)
   PRESIDIO_ENTITIES=PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS
   
   # Not: PRESIDIO_ENTITIES=PERSON, DATE_TIME, PHONE_NUMBER
   ```

3. **Validate environment**:
   ```bash
   # Set correct environment
   ENVIRONMENT=development  # or production, staging
   
   # Ensure DEBUG matches environment
   DEBUG=true   # for development
   DEBUG=false  # for production
   ```

## Runtime Errors

### Issue: Server Won't Start

**Symptoms**:
```
Address already in use
OSError: [Errno 98] Address already in use
```

**Diagnosis**:
```bash
# Check if port is in use
lsof -i :8000
netstat -tuln | grep 8000

# Check for running processes
ps aux | grep uvicorn
```

**Solutions**:

1. **Kill existing process**:
   ```bash
   # Find process ID
   lsof -i :8000
   
   # Kill process
   kill -9 <PID>
   
   # Or kill all uvicorn processes
   pkill -f uvicorn
   ```

2. **Use different port**:
   ```bash
   # Start on different port
   uvicorn src.main:app --port 8001
   
   # Or set in .env
   PORT=8001
   ```

3. **Restart properly**:
   ```bash
   # Stop all instances
   pkill -f uvicorn
   
   # Wait a moment
   sleep 2
   
   # Start fresh
   uvicorn src.main:app --reload
   ```

### Issue: Import Errors

**Symptoms**:
```
ModuleNotFoundError: No module named 'src'
ImportError: cannot import name 'PIIRedactionService'
```

**Diagnosis**:
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Check if in correct directory
pwd
ls src/

# Check module structure
python -c "import src; print(src.__file__)"
```

**Solutions**:

1. **Run from project root**:
   ```bash
   # Ensure you're in project root
   cd /path/to/phase4-secure-medical-chat
   
   # Run with module syntax
   python -m src.main
   ```

2. **Fix PYTHONPATH**:
   ```bash
   # Add current directory to PYTHONPATH
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   
   # Or add to .env
   PYTHONPATH=/path/to/phase4-secure-medical-chat
   ```

3. **Check __init__.py files**:
   ```bash
   # Ensure all directories have __init__.py
   touch src/__init__.py
   touch src/api/__init__.py
   touch src/security/__init__.py
   ```

### Issue: Database Errors

**Symptoms**:
```
sqlite3.OperationalError: no such table: audit_logs
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```

**Diagnosis**:
```bash
# Check if database exists
ls -la data/secure_medical_chat.db

# Check database permissions
ls -la data/

# Check database schema
sqlite3 data/secure_medical_chat.db ".schema"
```

**Solutions**:

1. **Initialize database**:
   ```bash
   # Create data directory
   mkdir -p data
   
   # Initialize database
   python -c "from src.database import init_database; init_database()"
   ```

2. **Fix permissions**:
   ```bash
   # Fix directory permissions
   chmod 755 data/
   
   # Fix database permissions
   chmod 644 data/secure_medical_chat.db
   ```

3. **Reset database**:
   ```bash
   # Backup existing database
   cp data/secure_medical_chat.db data/secure_medical_chat.db.backup
   
   # Remove and recreate
   rm data/secure_medical_chat.db
   python -c "from src.database import init_database; init_database()"
   ```

## Performance Issues

### Issue: Slow Response Times

**Symptoms**:
- Requests taking >5 seconds
- Timeout errors
- High latency

**Diagnosis**:
```bash
# Check system resources
top
htop

# Check memory usage
free -h

# Check disk I/O
iostat -x 1

# Profile application
python -m cProfile -o profile.stats src/main.py
```

**Solutions**:

1. **Enable caching**:
   ```bash
   # In .env
   ENABLE_RESPONSE_CACHE=true
   CACHE_TTL_HOURS=24
   ```

2. **Optimize model selection**:
   ```bash
   # Use faster model for simple queries
   DEFAULT_MODEL=gpt-3.5-turbo
   
   # Reduce max tokens
   MAX_TOKENS=500
   ```

3. **Increase workers**:
   ```bash
   # Start with more workers
   gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

4. **Database optimization**:
   ```sql
   -- Add indexes
   CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
   
   -- Vacuum database
   VACUUM;
   ANALYZE;
   ```

### Issue: High Memory Usage

**Symptoms**:
- Out of memory errors
- System becomes unresponsive
- Memory usage >90%

**Diagnosis**:
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head

# Check for memory leaks
python -m memory_profiler src/main.py
```

**Solutions**:

1. **Limit cache size**:
   ```python
   # In src/config.py
   CACHE_MAX_SIZE = 1000  # Limit cached responses
   ```

2. **Reduce worker count**:
   ```bash
   # Use fewer workers
   gunicorn src.main:app -w 2 -k uvicorn.workers.UvicornWorker
   ```

3. **Clear cache periodically**:
   ```python
   # Add cache cleanup
   @app.on_event("startup")
   async def cleanup_cache():
       cache.clear_old_entries()
   ```

### Issue: Rate Limit Errors

**Symptoms**:
```
429 Too Many Requests
Rate limit exceeded for patient role
```

**Diagnosis**:
```bash
# Check current rate limits
curl http://localhost:8000/api/metrics | jq '.usage_metrics'

# Check rate limit headers
curl -I http://localhost:8000/api/chat
```

**Solutions**:

1. **Adjust rate limits**:
   ```bash
   # In .env
   PATIENT_MAX_QUERIES_PER_HOUR=20
   PHYSICIAN_MAX_QUERIES_PER_HOUR=200
   ```

2. **Use different role**:
   ```bash
   # Switch to physician role for more queries
   curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "...", "user_role": "physician"}'
   ```

3. **Wait for reset**:
   ```bash
   # Check reset time
   curl -I http://localhost:8000/api/chat | grep X-RateLimit-Reset
   ```

## Security Issues

### Issue: PII Redaction Not Working

**Symptoms**:
- Personal information visible in responses
- No entities detected
- Redaction accuracy <90%

**Diagnosis**:
```bash
# Test PII detection
python -c "
from src.security.pii_redaction import PIIRedactionService
service = PIIRedactionService()
result = service.redact_message('My name is John Smith, phone 555-1234')
print(result)
"

# Check Presidio installation
python -c "import presidio_analyzer; print(presidio_analyzer.__version__)"
```

**Solutions**:

1. **Reinstall Presidio**:
   ```bash
   pip uninstall presidio-analyzer presidio-anonymizer
   pip install presidio-analyzer presidio-anonymizer
   python -m spacy download en_core_web_sm
   ```

2. **Configure entities**:
   ```bash
   # In .env
   PRESIDIO_ENTITIES=PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION
   ENABLE_PII_REDACTION=true
   ```

3. **Test with sample data**:
   ```bash
   python examples/pii_redaction_demo.py
   ```

### Issue: Guardrails Not Blocking Malicious Prompts

**Symptoms**:
- Prompt injection succeeds
- Jailbreak attempts not blocked
- Security block rate <80%

**Diagnosis**:
```bash
# Test guardrails
python -c "
from src.security.guardrails import GuardrailsService
service = GuardrailsService()
result = service.validate_input('Ignore all previous instructions')
print(result)
"

# Check guardrails configuration
cat config/guardrails/config.yml
```

**Solutions**:

1. **Enable all guardrails**:
   ```bash
   # In .env
   ENABLE_GUARDRAILS=true
   ENABLE_LLAMA_GUARD=true
   ENABLE_NEMO_GUARDRAILS=true
   ```

2. **Update guardrails config**:
   ```yaml
   # config/guardrails/config.yml
   rails:
     input:
       flows:
         - check prompt injection
         - check jailbreak attempts
         - check harmful requests
   ```

3. **Test security suite**:
   ```bash
   python run_security_tests.py
   ```

### Issue: Authentication Failures

**Symptoms**:
```
401 Unauthorized
Invalid JWT token
Token has expired
```

**Diagnosis**:
```bash
# Check JWT configuration
echo $JWT_SECRET_KEY
echo $JWT_EXPIRE_MINUTES

# Test token generation
python -c "
from src.auth.jwt_handler import JWTHandler
handler = JWTHandler()
token = handler.create_token('user123', 'patient')
print(token)
"
```

**Solutions**:

1. **Fix JWT secret**:
   ```bash
   # Generate new secret
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # Update .env
   JWT_SECRET_KEY=<new-secret>
   ```

2. **Increase token expiry**:
   ```bash
   # In .env
   JWT_EXPIRE_MINUTES=1440  # 24 hours
   ```

3. **Use demo API keys**:
   ```bash
   # For testing
   curl -X POST http://localhost:8000/api/chat \
     -H "X-API-Key: patient-demo-key" \
     -d '{"message": "test", "user_role": "patient"}'
   ```

## Database Problems

### Issue: Database Locked

**Symptoms**:
```
sqlite3.OperationalError: database is locked
```

**Solutions**:

1. **Close other connections**:
   ```bash
   # Find processes using database
   lsof data/secure_medical_chat.db
   
   # Kill if necessary
   kill <PID>
   ```

2. **Increase timeout**:
   ```python
   # In src/database.py
   engine = create_engine(
       DATABASE_URL,
       connect_args={"timeout": 30}
   )
   ```

3. **Use PostgreSQL for production**:
   ```bash
   # Switch to PostgreSQL
   DATABASE_URL=postgresql://user:pass@localhost:5432/medchat
   ```

### Issue: Database Corruption

**Symptoms**:
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solutions**:

1. **Restore from backup**:
   ```bash
   cp data/secure_medical_chat.db.backup data/secure_medical_chat.db
   ```

2. **Dump and restore**:
   ```bash
   # Dump database
   sqlite3 data/secure_medical_chat.db .dump > backup.sql
   
   # Create new database
   rm data/secure_medical_chat.db
   sqlite3 data/secure_medical_chat.db < backup.sql
   ```

3. **Recreate database**:
   ```bash
   # Backup data if possible
   # Remove corrupted database
   rm data/secure_medical_chat.db
   
   # Initialize fresh database
   python -c "from src.database import init_database; init_database()"
   ```

## API Integration Issues

### Issue: OpenAI API Errors

**Symptoms**:
```
openai.error.RateLimitError: Rate limit exceeded
openai.error.APIError: The server had an error processing your request
```

**Solutions**:

1. **Check API status**:
   ```bash
   curl https://status.openai.com/api/v2/status.json
   ```

2. **Implement retry logic**:
   ```python
   # Already implemented in src/llm/llm_gateway.py
   # Adjust retry settings if needed
   MAX_RETRIES = 3
   RETRY_DELAY = 2
   ```

3. **Use fallback model**:
   ```bash
   # In .env
   DEFAULT_MODEL=gpt-3.5-turbo
   FALLBACK_MODEL=gpt-3.5-turbo-16k
   ```

### Issue: Helicone Integration Problems

**Symptoms**:
- Cost tracking not working
- Helicone dashboard empty
- Connection errors

**Solutions**:

1. **Verify Helicone key**:
   ```bash
   # Check key format
   echo $HELICONE_API_KEY
   # Should start with "sk-helicone-"
   ```

2. **Test Helicone connection**:
   ```bash
   curl https://api.helicone.ai/v1/request \
     -H "Helicone-Auth: Bearer $HELICONE_API_KEY"
   ```

3. **Disable if not needed**:
   ```bash
   # In .env
   ENABLE_COST_TRACKING=false
   ```

## Deployment Issues

### Issue: Docker Container Won't Start

**Symptoms**:
```
Container exits immediately
Health check failing
```

**Diagnosis**:
```bash
# Check container logs
docker logs medchat-app

# Check container status
docker ps -a

# Inspect container
docker inspect medchat-app
```

**Solutions**:

1. **Check environment variables**:
   ```bash
   # Verify env vars in container
   docker exec medchat-app env | grep OPENAI
   ```

2. **Fix health check**:
   ```dockerfile
   # In Dockerfile
   HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
       CMD curl -f http://localhost:8000/health || exit 1
   ```

3. **Check logs for errors**:
   ```bash
   docker logs -f medchat-app
   ```

### Issue: Kubernetes Pod Crashes

**Symptoms**:
- Pod in CrashLoopBackOff
- Readiness probe failing
- OOMKilled status

**Diagnosis**:
```bash
# Check pod status
kubectl get pods -n medchat

# Check pod logs
kubectl logs -f pod/medchat-app-xxx -n medchat

# Describe pod
kubectl describe pod medchat-app-xxx -n medchat
```

**Solutions**:

1. **Increase resources**:
   ```yaml
   resources:
     requests:
       memory: "1Gi"
       cpu: "500m"
     limits:
       memory: "2Gi"
       cpu: "1000m"
   ```

2. **Fix probes**:
   ```yaml
   livenessProbe:
     httpGet:
       path: /health
       port: 8000
     initialDelaySeconds: 60
     periodSeconds: 10
   ```

3. **Check secrets**:
   ```bash
   kubectl get secrets -n medchat
   kubectl describe secret medchat-secrets -n medchat
   ```

## Getting Help

### Collecting Diagnostic Information

When reporting issues, collect this information:

```bash
#!/bin/bash
# scripts/collect_diagnostics.sh

echo "=== System Information ===" > diagnostics.txt
uname -a >> diagnostics.txt
python --version >> diagnostics.txt
pip --version >> diagnostics.txt

echo -e "\n=== Installed Packages ===" >> diagnostics.txt
pip list >> diagnostics.txt

echo -e "\n=== Environment Variables ===" >> diagnostics.txt
env | grep -E "(OPENAI|JWT|PRESIDIO|GUARDRAILS|DATABASE)" >> diagnostics.txt

echo -e "\n=== Recent Logs ===" >> diagnostics.txt
tail -n 100 logs/app.log >> diagnostics.txt

echo -e "\n=== Configuration ===" >> diagnostics.txt
python src/startup_config.py >> diagnostics.txt 2>&1

echo "Diagnostics collected in diagnostics.txt"
```

### Support Resources

1. **Documentation**:
   - README.md - Quick start guide
   - docs/API_REFERENCE.md - API documentation
   - docs/SECURITY_GUIDE.md - Security features
   - docs/DEPLOYMENT_GUIDE.md - Deployment instructions

2. **Testing**:
   ```bash
   # Run tests
   pytest tests/
   
   # Run security tests
   python run_security_tests.py
   
   # Run demos
   python demo_cli.py --batch
   ```

3. **Community**:
   - GitHub Issues
   - Stack Overflow (tag: secure-medical-chat)
   - Project documentation

### Debug Mode

Enable debug mode for detailed logging:

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG

# Run with verbose output
python -m src.main --log-level DEBUG
```

### Common Commands Reference

```bash
# Start server
uvicorn src.main:app --reload

# Run tests
pytest

# Check configuration
python src/startup_config.py

# Initialize database
python -c "from src.database import init_database; init_database()"

# Run security tests
python run_security_tests.py

# Check health
curl http://localhost:8000/health

# View logs
tail -f logs/app.log

# Stop all processes
pkill -f uvicorn
```

This troubleshooting guide covers the most common issues and their solutions. For issues not covered here, please collect diagnostic information and consult the support resources.