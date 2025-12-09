# Phase 4: Secure Medical Chat with Guardrails

A proof-of-concept conversational AI system for healthcare that demonstrates critical security, privacy, and optimization patterns. This system implements PII/PHI redaction, prompt injection defense, cost optimization, role-based access control, and comprehensive audit logging.

## 🎯 Learning Objectives

- Implement PII/PHI redaction pipelines with Microsoft Presidio
- Deploy prompt injection and jailbreak defenses using NeMo Guardrails/Llama-Guard-3
- Use Helicone for cost tracking and optimization
- Demonstrate RBAC concepts and audit logging patterns
- Build secure AI systems with privacy guarantees

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client API    │───▶│  Security Layer │───▶│   LLM Gateway   │
│                 │    │                 │    │                 │
│ - REST API      │    │ - PII Redaction │    │ - Helicone      │
│ - Role Auth     │    │ - Guardrails    │    │ - Model Router  │
│ - Input Valid   │    │ - Rate Limiting │    │ - Cache Layer   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key
- Helicone API key (optional, for cost tracking)

### Setup

1. **Clone and setup environment**:
   ```bash
   git clone <repository-url>
   cd phase4-secure-medical-chat
   
   # Create virtual environment (NOT conda/anaconda)
   python -m venv venv
   
   # Activate virtual environment
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Initialize database**:
   ```bash
   python -m src.database.init_db
   ```

4. **Run the application**:
   ```bash
   uvicorn src.main:app --reload
   ```

## 🔒 Security Features

### PII/PHI Redaction
- **Microsoft Presidio** integration for detecting sensitive information
- **Typed placeholders** ([PERSON_1], [DATE_1]) for anonymization
- **De-anonymization** for response processing
- **90%+ detection accuracy** on medical conversations

### Guardrails & Safety
- **NeMo Guardrails** for prompt injection defense
- **Llama-Guard-3** for content classification
- **Medical disclaimers** automatically added
- **Emergency response** detection (911 recommendations)

### Access Control
- **Role-based permissions** (patient, physician, admin)
- **JWT authentication** with session management
- **Rate limiting** per user role
- **API key** authentication support

## 💰 Cost Optimization

- **Helicone proxy** for cost tracking and analytics
- **Intelligent model routing** (GPT-3.5 vs GPT-4)
- **Response caching** with 24-hour TTL
- **Token usage optimization**
- **Cost breakdown** by model and user role

## 📊 Monitoring & Audit

- **Comprehensive audit logging** of all interactions
- **Security event tracking** (blocked prompts, auth failures)
- **Cost metrics dashboard**
- **Performance monitoring** (latency, cache hit rates)

## 🔧 API Endpoints

### Chat Endpoint
```bash
POST /api/chat
{
  "message": "I have chest pain and shortness of breath",
  "user_role": "patient",
  "session_id": "session_123"
}
```

### Metrics Endpoint
```bash
GET /api/metrics
# Returns cost breakdown, usage stats, cache hit rates
```

### Admin Endpoints
```bash
GET /api/audit-logs    # Admin only
GET /api/security-events    # Admin only
GET /api/health        # System status
```

## 🧪 Testing

### Security Testing
```bash
# Run PII/PHI detection tests
python -m pytest tests/security/test_pii_redaction.py

# Run prompt injection tests
python -m pytest tests/security/test_guardrails.py

# Run red-team security tests
python -m pytest tests/security/test_red_team.py
```

### Integration Testing
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=src
```

## 📈 Performance Targets

- **Response latency**: <2 seconds (including all security checks)
- **PII detection accuracy**: ≥90%
- **Prompt injection blocking**: ≥80%
- **Cache hit rate**: >20% for similar queries

## 🛡️ Security Validation

The system includes comprehensive red-team testing with:
- 15 adversarial prompts for prompt injection
- 20 medical conversations for PII/PHI detection
- Jailbreak attempt prevention
- Authentication bypass testing

## 📚 Documentation

- [API Reference](docs/api.md)
- [Security Guide](docs/security.md)
- [Deployment Guide](docs/deployment.md)
- [Configuration Reference](docs/configuration.md)

## 🤝 Contributing

This is a proof-of-concept project for learning AI security patterns. See the implementation tasks in `.kiro/specs/phase4-secure-medical-chat/tasks.md`.

## ⚠️ Disclaimer

This is a demonstration system for educational purposes only. Not intended for production use with real patient data. Always consult healthcare providers for medical advice.

## 📄 License

MIT License - see LICENSE file for details.