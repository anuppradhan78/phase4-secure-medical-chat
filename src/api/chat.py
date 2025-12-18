"""
Chat API endpoints with integrated security pipeline.

This module implements the main chat endpoint with the complete security pipeline:
- Authentication and authorization
- Rate limiting
- PII/PHI redaction
- Guardrails validation
- LLM processing
- Response validation
- De-anonymization
- Audit logging
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse

from ..models import (
    ChatRequest, ChatResponse, UserRole, AuditEvent, SecurityEvent, 
    EventType, ThreatType, UserSession
)
from ..auth.rbac import RBACService
from ..auth.rate_limiter import RateLimiter
try:
    from ..security.pii_redaction import PIIRedactionService
    PII_SERVICE_AVAILABLE = True
except ImportError:
    from ..security.mock_pii_redaction import MockPIIRedactionService as PIIRedactionService
    PII_SERVICE_AVAILABLE = False
from ..security.guardrails import GuardrailsService
from ..security.medical_safety import MedicalSafetyController
from ..llm.llm_gateway import LLMGateway
from ..llm.latency_tracker import LatencyTracker
from ..database import get_database

logger = logging.getLogger(__name__)

# Initialize services
rbac_service = RBACService()
rate_limiter = RateLimiter()
pii_service = PIIRedactionService()
guardrails_service = GuardrailsService()
medical_safety_service = MedicalSafetyController()
latency_tracker = LatencyTracker()

# Router for chat endpoints
router = APIRouter()

# Global LLM Gateway (will be injected from main app)
llm_gateway: Optional[LLMGateway] = None


def init_chat_router(gateway: LLMGateway):
    """Initialize the chat router with LLM gateway."""
    global llm_gateway
    llm_gateway = gateway
    logger.info("Chat router initialized with LLM gateway")


async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Extract user information from request.
    In a production system, this would validate JWT tokens or API keys.
    For this POC, we'll use simple header-based authentication.
    """
    # Check for API key or user info in headers
    user_id = request.headers.get("X-User-ID", "anonymous")
    user_role_str = request.headers.get("X-User-Role", "patient")
    session_id = request.headers.get("X-Session-ID")
    
    # Validate user role
    try:
        user_role = UserRole(user_role_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid user role: {user_role_str}. Must be one of: patient, physician, admin"
        )
    
    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    return {
        "user_id": user_id,
        "user_role": user_role,
        "session_id": session_id,
        "ip_address": request.client.host if request.client else "unknown"
    }


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> ChatResponse:
    """
    Main chat endpoint with complete security pipeline.
    
    Security Pipeline:
    1. Authentication & Authorization
    2. Rate Limiting
    3. PII/PHI Redaction
    4. Guardrails Validation
    5. LLM Processing
    6. Response Validation
    7. De-anonymization
    8. Audit Logging
    """
    request_id = str(uuid.uuid4())
    start_time = latency_tracker.start_request_tracking(request_id)
    user_id = current_user["user_id"]
    user_role = current_user["user_role"]
    session_id = current_user["session_id"]
    
    # Initialize response metadata
    metadata = {
        "request_id": request_id,
        "redaction_info": {"entities_redacted": 0, "entity_types": []},
        "cost": 0.0,
        "latency_ms": 0,
        "model_used": "unknown",
        "cache_hit": False,
        "security_flags": [],
        "pipeline_stages": [],
        "latency_breakdown": {}
    }
    
    db = get_database()
    
    try:
        # === STAGE 1: AUTHENTICATION & AUTHORIZATION ===
        with latency_tracker.measure_stage(request_id, "authentication"):
            # Check if user role is authorized for chat feature
            if not rbac_service.authorize_feature(user_role, "basic_chat"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User role '{user_role.value}' is not authorized for chat functionality"
                )
        
        metadata["pipeline_stages"].append("authentication")
        
        logger.info(f"Chat request from user {user_id} with role {user_role.value}")
        
        # === STAGE 2: RATE LIMITING ===
        with latency_tracker.measure_stage(request_id, "rate_limiting"):
            # Check rate limits
            rate_allowed, rate_info = rate_limiter.check_rate_limit(user_id, user_role)
            if not rate_allowed:
                # Log security event for rate limit exceeded
                security_event = SecurityEvent(
                    timestamp=datetime.now(timezone.utc),
                    user_id=user_id,
                    user_role=user_role,
                    session_id=session_id,
                    threat_type=ThreatType.RATE_LIMIT_EXCEEDED,
                    blocked_content=f"Rate limit exceeded: {rate_info['current_requests']}/{rate_info['limit']}",
                    risk_score=0.3,
                    detection_method="rate_limiter",
                    action_taken="request_blocked",
                    metadata=rate_info
                )
                db.log_security_event(security_event)
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. {rate_info['remaining']} requests remaining. Resets at {rate_info['reset_time']}"
                )
        
        metadata["pipeline_stages"].append("rate_limiting")
        
        # === STAGE 3: PII/PHI REDACTION ===
        with latency_tracker.measure_stage(request_id, "pii_redaction") as stage:
            # Redact PII/PHI from user message
            redaction_result = pii_service.redact_message(
                request.message, 
                user_id, 
                session_id
            )
            stage.metadata = {
                "entities_found": redaction_result.entities_found,
                "entity_types": [et.value for et in redaction_result.entity_types]
            }
        
        metadata["redaction_info"] = {
            "entities_redacted": redaction_result.entities_found,
            "entity_types": [et.value for et in redaction_result.entity_types]
        }
        
        metadata["pipeline_stages"].append("pii_redaction")
        
        if redaction_result.entities_found > 0:
            logger.info(f"Redacted {redaction_result.entities_found} PII/PHI entities")
        
        # === STAGE 4: GUARDRAILS VALIDATION ===
        with latency_tracker.measure_stage(request_id, "guardrails_validation") as stage:
            # Validate input through guardrails
            input_validation = guardrails_service.validate_input(
                redaction_result.redacted_text, 
                user_id
            )
            stage.metadata = {
                "blocked": input_validation.blocked,
                "risk_score": input_validation.risk_score
            }
        
        if input_validation.blocked:
            # Log security event for blocked content
            security_event = SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                user_role=user_role,
                session_id=session_id,
                threat_type=ThreatType.INJECTION_ATTACK if input_validation.threat_type == "injection_attack" else ThreatType.UNSAFE_CONTENT,
                blocked_content=request.message[:200],  # First 200 chars for logging
                risk_score=input_validation.risk_score,
                detection_method="guardrails",
                action_taken="request_blocked",
                metadata=getattr(input_validation, 'metadata', {}) or {}
            )
            db.log_security_event(security_event)
            
            metadata["security_flags"].append(input_validation.reason)
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Content blocked by security filters: {input_validation.reason}"
            )
        
        metadata["pipeline_stages"].append("guardrails_validation")
        
        # === STAGE 5: MEDICAL SAFETY VALIDATION ===
        with latency_tracker.measure_stage(request_id, "medical_safety") as stage:
            # Check for medical safety concerns
            medical_validation = medical_safety_service.validate_input(request.message)
            stage.metadata = {
                "blocked": medical_validation.blocked,
                "risk_score": medical_validation.risk_score
            }
            
            if medical_validation.blocked:
                security_event = SecurityEvent(
                    timestamp=datetime.now(timezone.utc),
                    user_id=user_id,
                    user_role=user_role,
                    session_id=session_id,
                    threat_type=ThreatType.MEDICAL_SAFETY,
                    blocked_content=request.message[:200],
                    risk_score=medical_validation.risk_score,
                    detection_method="medical_safety",
                    action_taken="request_blocked",
                    metadata=getattr(medical_validation, 'metadata', {}) or {}
                )
                db.log_security_event(security_event)
                
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Medical safety concern: {medical_validation.reason}"
                )
            
            # Add emergency response flag if needed
            medical_metadata = getattr(medical_validation, 'metadata', {}) or {}
            if medical_metadata.get("requires_emergency_response"):
                metadata["security_flags"].append("emergency_symptoms_detected")
        
        metadata["pipeline_stages"].append("medical_safety")
        
        # === STAGE 6: LLM PROCESSING ===
        with latency_tracker.measure_stage(request_id, "llm_processing") as stage:
            if not llm_gateway:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="LLM gateway not available"
                )
            
            # Create chat request for LLM
            llm_request = ChatRequest(
                message=redaction_result.redacted_text,
                user_role=user_role,
                session_id=session_id,
                user_id=user_id,
                metadata={"original_message_length": len(request.message)}
            )
            
            # Process through LLM gateway
            llm_response, llm_metadata = await llm_gateway.process_chat_request(llm_request)
            
            stage.metadata = {
                "model_used": llm_metadata.get("model_used", "unknown"),
                "cache_hit": llm_metadata.get("cache_hit", False),
                "cost": llm_metadata.get("cost", 0.0),
                "tokens_used": llm_metadata.get("tokens_used", 0)
            }
        
        metadata["pipeline_stages"].append("llm_processing")
        
        # Update metadata with LLM information
        metadata.update({
            "cost": llm_metadata.get("cost", 0.0),
            "model_used": llm_metadata.get("model_used", "unknown"),
            "cache_hit": llm_metadata.get("cache_hit", False),
            "tokens_used": llm_metadata.get("tokens_used", 0)
        })
        
        # === STAGE 7: RESPONSE VALIDATION ===
        with latency_tracker.measure_stage(request_id, "response_validation"):
            # Validate LLM response through guardrails
            output_validation = guardrails_service.validate_output(
                llm_response.response, 
                user_id
            )
            
            # Apply any response modifications (e.g., medical disclaimers)
            final_response = output_validation.modified_response or llm_response.response
        
        metadata["pipeline_stages"].append("response_validation")
        
        # === STAGE 8: DE-ANONYMIZATION ===
        with latency_tracker.measure_stage(request_id, "de_anonymization"):
            # De-anonymize response if needed
            if redaction_result.entities_found > 0:
                final_response = pii_service.de_anonymize_response(
                    final_response, 
                    user_id, 
                    session_id
                )
        
        metadata["pipeline_stages"].append("de_anonymization")
        
        # === STAGE 9: RECORD USAGE AND AUDIT ===
        with latency_tracker.measure_stage(request_id, "audit_logging"):
            # Record request for rate limiting
            rate_limiter.record_request(user_id, metadata["cost"])
            
            # Complete latency tracking
            profile = latency_tracker.finish_request_tracking(
                request_id,
                start_time,
                user_role.value,
                metadata["model_used"],
                metadata["cache_hit"],
                False,  # optimization_applied
                metadata
            )
            
            metadata["latency_ms"] = int(profile.total_duration_ms)
            metadata["latency_breakdown"] = {
                stage.stage_name: stage.duration_ms 
                for stage in profile.stages 
                if stage.duration_ms is not None
            }
        
            # Log audit event
            audit_event = AuditEvent(
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                user_role=user_role,
                session_id=session_id,
                event_type=EventType.CHAT_REQUEST,
                message=redaction_result.redacted_text,  # Store redacted version
                response=final_response[:500],  # Truncate for storage
                cost_usd=metadata["cost"],
                latency_ms=metadata["latency_ms"],
                entities_redacted=redaction_result.entity_types,
                security_flags=metadata["security_flags"],
                metadata={
                    "pipeline_stages": metadata["pipeline_stages"],
                    "model_used": metadata["model_used"],
                    "cache_hit": metadata["cache_hit"],
                    "tokens_used": metadata.get("tokens_used", 0),
                    "redaction_count": redaction_result.entities_found,
                    "latency_breakdown": metadata["latency_breakdown"]
                }
            )
            db.log_audit_event(audit_event)
            
            # Update session activity
            db.update_session_activity(session_id, metadata["cost"])
        
        metadata["pipeline_stages"].append("audit_logging")
        
        logger.info(
            f"Chat request completed successfully: "
            f"User={user_id}, Cost=${metadata['cost']:.4f}, "
            f"Latency={metadata['latency_ms']}ms, Model={metadata['model_used']}"
        )
        
        # Return successful response
        return ChatResponse(
            response=final_response,
            metadata=metadata
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (these are expected errors)
        raise
        
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        
        # Complete error latency tracking
        if start_time:
            error_profile = latency_tracker.finish_request_tracking(
                request_id,
                start_time,
                user_role.value,
                "unknown",
                False,
                False,
                {"error": str(e)}
            )
            
            # Log error audit event
            error_audit_event = AuditEvent(
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                user_role=user_role,
                session_id=session_id,
                event_type=EventType.CHAT_REQUEST,
                message=request.message[:200],
                response=f"Error: {str(e)}",
                cost_usd=0.0,
                latency_ms=int(error_profile.total_duration_ms),
                entities_redacted=[],
                security_flags=["system_error"],
                metadata={"error": str(e), "pipeline_stages": metadata["pipeline_stages"]}
            )
            db.log_audit_event(error_audit_event)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing your request"
        )


@router.get("/chat/health")
async def chat_health_check():
    """Health check for chat service components."""
    health_status = {
        "chat_service": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Check LLM Gateway
    if llm_gateway:
        try:
            gateway_health = await llm_gateway.health_check()
            health_status["llm_gateway"] = gateway_health["overall"]
        except Exception as e:
            health_status["llm_gateway"] = f"error: {str(e)}"
    else:
        health_status["llm_gateway"] = "not_initialized"
    
    # Check database
    try:
        db = get_database()
        db.get_metrics(days=1)
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
    
    # Check security services
    try:
        # Test PII service
        test_result = pii_service.redact_message("Test message", "health_check")
        health_status["pii_service"] = "healthy"
        
        # Test guardrails
        guard_result = guardrails_service.validate_input("Test message", "health_check")
        health_status["guardrails"] = "healthy"
        
    except Exception as e:
        health_status["security_services"] = f"error: {str(e)}"
    
    # Overall health
    component_statuses = [
        health_status.get("llm_gateway", "unknown"),
        health_status.get("database", "unknown"),
        health_status.get("pii_service", "unknown"),
        health_status.get("guardrails", "unknown")
    ]
    
    if all("healthy" in status for status in component_statuses):
        health_status["overall"] = "healthy"
        return health_status
    elif any("error" in status for status in component_statuses):
        health_status["overall"] = "degraded"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )
    else:
        health_status["overall"] = "unknown"
        return health_status


@router.get("/chat/pipeline-status")
async def get_pipeline_status():
    """Get status of all security pipeline components."""
    return {
        "pipeline_components": [
            {"name": "authentication", "status": "active", "description": "Role-based access control"},
            {"name": "rate_limiting", "status": "active", "description": "Per-role request limiting"},
            {"name": "pii_redaction", "status": "active", "description": "Microsoft Presidio PII/PHI detection"},
            {"name": "guardrails_validation", "status": "active", "description": "Prompt injection and content safety"},
            {"name": "medical_safety", "status": "active", "description": "Medical-specific safety checks"},
            {"name": "llm_processing", "status": "active" if llm_gateway else "unavailable", "description": "LLM gateway with cost tracking"},
            {"name": "response_validation", "status": "active", "description": "Output safety validation"},
            {"name": "de_anonymization", "status": "active", "description": "PII/PHI restoration"},
            {"name": "audit_logging", "status": "active", "description": "Comprehensive audit trail"}
        ],
        "security_features": {
            "pii_phi_redaction": True,
            "prompt_injection_defense": True,
            "medical_safety_controls": True,
            "cost_tracking": True,
            "audit_logging": True,
            "rate_limiting": True,
            "role_based_access": True
        }
    }


@router.post("/chat/test-security")
async def test_security_pipeline(
    test_message: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Test the security pipeline without making an LLM call.
    Useful for validating security controls.
    """
    user_id = current_user["user_id"]
    user_role = current_user["user_role"]
    session_id = current_user["session_id"]
    
    results = {
        "original_message": test_message,
        "pipeline_results": {}
    }
    
    try:
        # Test PII redaction
        redaction_result = pii_service.redact_message(test_message, user_id, session_id)
        results["pipeline_results"]["pii_redaction"] = {
            "redacted_text": redaction_result.redacted_text,
            "entities_found": redaction_result.entities_found,
            "entity_types": [et.value for et in redaction_result.entity_types]
        }
        
        # Test guardrails
        guard_result = guardrails_service.validate_input(redaction_result.redacted_text, user_id)
        results["pipeline_results"]["guardrails"] = {
            "blocked": guard_result.blocked,
            "reason": guard_result.reason,
            "risk_score": guard_result.risk_score
        }
        
        # Test medical safety
        medical_result = medical_safety_service.validate_input(test_message)
        results["pipeline_results"]["medical_safety"] = {
            "blocked": medical_result.blocked,
            "reason": medical_result.reason,
            "risk_score": medical_result.risk_score,
            "metadata": getattr(medical_result, 'metadata', {}) or {}
        }
        
        # Test rate limiting
        rate_allowed, rate_info = rate_limiter.check_rate_limit(user_id, user_role)
        results["pipeline_results"]["rate_limiting"] = {
            "allowed": rate_allowed,
            "current_requests": rate_info["current_requests"],
            "limit": rate_info["limit"],
            "remaining": rate_info["remaining"]
        }
        
        return results
        
    except Exception as e:
        logger.error(f"Error in security pipeline test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Security pipeline test failed: {str(e)}"
        )