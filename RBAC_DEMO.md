# Role-Based Access Control (RBAC) System Demonstration

This document demonstrates the complete RBAC implementation for the Secure Medical Chat system, showing JWT authentication, role-based permissions, rate limiting, and session management.

## System Overview

The RBAC system implements three user roles with different access levels:

### 🏥 **Patient Role**
- **Max Queries/Hour**: 10
- **Allowed Models**: gpt-3.5-turbo
- **Cost Limit/Hour**: $1.00
- **Max Tokens/Query**: 500
- **Features**: 
  - basic_chat
  - symptom_checker
  - health_information
  - appointment_scheduling

### 👨‍⚕️ **Physician Role**
- **Max Queries/Hour**: 100
- **Allowed Models**: gpt-3.5-turbo, gpt-4
- **Cost Limit/Hour**: $10.00
- **Max Tokens/Query**: 1000
- **Features**:
  - basic_chat
  - advanced_chat
  - diagnosis_support
  - research_access
  - clinical_guidelines
  - drug_interactions
  - medical_calculations

### 👨‍💼 **Admin Role**
- **Max Queries/Hour**: 1000
- **Allowed Models**: gpt-3.5-turbo, gpt-4, gpt-4-turbo
- **Cost Limit/Hour**: $50.00
- **Max Tokens/Query**: 2000
- **Features**: All features plus:
  - metrics_access
  - audit_logs
  - user_management
  - system_configuration
  - security_monitoring

## API Endpoints

### Authentication Endpoints

#### Create Demo Tokens
```bash
# Patient token
curl -X POST "http://localhost:8000/auth/demo/patient-token"

# Physician token  
curl -X POST "http://localhost:8000/auth/demo/physician-token"

# Admin token
curl -X POST "http://localhost:8000/auth/demo/admin-token"
```

#### Get Current User Info
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/auth/me"
```

#### Get Rate Limit Status
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8000/auth/rate-limit"
```

### Role-Based Access Examples

#### Public Endpoints (No Authentication Required)
```bash
# Get role comparison
curl "http://localhost:8000/auth/roles"

# Get rate limits for all roles
curl "http://localhost:8000/auth/limits"
```

#### Admin-Only Endpoints
```bash
# Get session statistics (Admin only)
curl -H "Authorization: Bearer ADMIN_TOKEN" \
     "http://localhost:8000/auth/admin/sessions"

# Reset user rate limits (Admin only)
curl -X POST -H "Authorization: Bearer ADMIN_TOKEN" \
     "http://localhost:8000/auth/admin/reset-limits/user123"
```

## Demonstration Results

### 1. JWT Token Generation ✅
- Successfully generates tokens for all roles
- Tokens contain user ID, role, and expiration
- Tokens are properly validated and decoded

### 2. Role-Based Feature Access ✅

| Feature | Patient | Physician | Admin |
|---------|---------|-----------|-------|
| basic_chat | ✅ | ✅ | ✅ |
| diagnosis_support | ❌ | ✅ | ✅ |
| audit_logs | ❌ | ❌ | ✅ |
| user_management | ❌ | ❌ | ✅ |

### 3. Model Access Control ✅

| Model | Patient | Physician | Admin |
|-------|---------|-----------|-------|
| gpt-3.5-turbo | ✅ | ✅ | ✅ |
| gpt-4 | ❌ | ✅ | ✅ |
| gpt-4-turbo | ❌ | ❌ | ✅ |

### 4. Rate Limiting ✅
- **Patient**: 10 requests/hour, $1.00/hour
- **Physician**: 100 requests/hour, $10.00/hour  
- **Admin**: 1000 requests/hour, $50.00/hour
- Properly enforces limits and tracks usage

### 5. Session Management ✅
- Creates unique sessions with expiration (24 hours default)
- Tracks request count and total cost per session
- Supports session validation and activity updates
- Allows session revocation and cleanup

### 6. API Access Control ✅
- Admin endpoints return 403 for non-admin users
- Authenticated endpoints require valid JWT tokens
- Public endpoints accessible without authentication
- Proper HTTP status codes and error messages

## Testing the System

### Run Unit Tests
```bash
cd phase4-secure-medical-chat
python -m pytest tests/test_rbac.py -v
```

### Run RBAC Demo
```bash
python test_rbac_simple.py
```

### Run API Integration Test
```bash
python test_api_integration.py
```

### Start Full API Server
```bash
uvicorn src.main:app --reload
```

## Security Features Demonstrated

### ✅ JWT Authentication
- Secure token generation with expiration
- Token validation and user extraction
- Role-based token creation

### ✅ Authorization Controls
- Feature-based access control
- Model-based access control
- Request limit validation

### ✅ Rate Limiting
- Per-user request tracking
- Role-based limits enforcement
- Cost-based limiting

### ✅ Session Management
- Secure session creation and tracking
- Activity monitoring and cost tracking
- Session expiration and cleanup

### ✅ Different Access Levels
- **Patients**: Basic health information access
- **Physicians**: Advanced medical AI capabilities
- **Admins**: Full system access and monitoring

## Requirements Validation

All requirements from the task have been successfully implemented:

- ✅ **4.1**: JWT token generation and validation
- ✅ **4.2**: Role-based permissions (patient, physician, admin)
- ✅ **4.3**: Rate limiting per user role (10/100/1000 per hour)
- ✅ **4.4**: Session management with expiration
- ✅ **4.5**: Different access levels demonstrated through API responses

The RBAC system provides a comprehensive foundation for secure medical chat applications with proper authentication, authorization, and resource management.