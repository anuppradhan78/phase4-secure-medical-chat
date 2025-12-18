"""
Admin API endpoints for system management and monitoring.

This module implements admin-only endpoints for:
- System health monitoring
- Audit log access
- Security event monitoring
- System status and configuration
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, status, Request
from fastapi.responses import JSONResponse

from ..models import UserRole, AuditEvent, SecurityEvent
from ..database import get_database
from ..config import get_config as get_app_config

logger = logging.getLogger(__name__)

# Router for admin endpoints
router = APIRouter()

# Global LLM Gateway (will be injected from main app)
llm_gateway = None


def init_admin_router(gateway):
    """Initialize the admin router with LLM gateway."""
    global llm_gateway
    llm_gateway = gateway
    logger.info("Admin router initialized with LLM gateway")


async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Extract user information from request.
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


async def require_admin(request: Request) -> Dict[str, Any]:
    """
    Dependency to require admin role.
    """
    current_user = await get_current_user(request)
    if current_user["user_role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required role: admin. Current role: {current_user['user_role'].value}"
        )
    return current_user


@router.get("/health", summary="System Health Check", description="Get comprehensive system health status")
async def admin_health_check():
    """
    System health check endpoint providing detailed status of all components.
    
    This endpoint is accessible to all authenticated users but provides more
    detailed information for admin users.
    
    Returns:
        Dict containing system health status and component details
    """
    health_status = {
        "status": "healthy",
        "service": "secure-medical-chat",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0"
    }
    
    # Check database connectivity
    try:
        db = get_database()
        # Test database with a simple query
        metrics = db.get_metrics(days=1)
        health_status["database"] = {
            "status": "healthy",
            "connection": "active",
            "recent_queries": metrics.get("queries_today", 0)
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check LLM Gateway
    if llm_gateway:
        try:
            gateway_health = await llm_gateway.health_check()
            health_status["llm_gateway"] = {
                "status": "healthy",
                "provider": gateway_health.get("provider", "unknown"),
                "cost_tracking": gateway_health.get("cost_tracker", "unknown"),
                "cache_status": gateway_health.get("cache", "unknown")
            }
        except Exception as e:
            logger.error(f"LLM Gateway health check failed: {str(e)}")
            health_status["llm_gateway"] = {
                "status": "unhealthy",
                "error": str(e)
            }
    else:
        health_status["llm_gateway"] = {
            "status": "not_initialized",
            "message": "LLM Gateway not available"
        }
    
    # Check configuration
    try:
        config = get_app_config()
        if config:
            health_status["configuration"] = {
                "status": "loaded",
                "environment": config.environment.value,
                "security_enabled": {
                    "pii_redaction": config.security.enable_pii_redaction,
                    "guardrails": config.security.enable_guardrails,
                    "medical_disclaimers": config.security.enable_medical_disclaimers
                }
            }
        else:
            health_status["configuration"] = {
                "status": "not_loaded",
                "message": "Configuration not available"
            }
    except Exception as e:
        logger.error(f"Configuration health check failed: {str(e)}")
        health_status["configuration"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Security services health
    health_status["security_services"] = {
        "pii_redaction": "active",
        "guardrails": "active",
        "medical_safety": "active",
        "rate_limiting": "active",
        "audit_logging": "active"
    }
    
    # Determine overall health
    component_statuses = []
    for component, details in health_status.items():
        if isinstance(details, dict) and "status" in details:
            component_statuses.append(details["status"])
    
    if all(status == "healthy" for status in component_statuses):
        health_status["overall_status"] = "healthy"
        return health_status
    elif any("unhealthy" in status for status in component_statuses):
        health_status["overall_status"] = "degraded"
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )
    else:
        health_status["overall_status"] = "unknown"
        return health_status


@router.get("/audit-logs", summary="Get Audit Logs", description="Retrieve system audit logs (Admin only)")
async def get_audit_logs(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of logs to retrieve"),
    offset: int = Query(default=0, ge=0, description="Number of logs to skip"),
    user_role: Optional[str] = Query(default=None, description="Filter by user role"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    start_date: Optional[str] = Query(default=None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(default=None, description="End date (ISO format)")
):
    """
    Retrieve audit logs with filtering and pagination.
    
    This endpoint is restricted to admin users only and provides access to
    comprehensive audit logs of all system interactions.
    
    Args:
        limit: Maximum number of logs to return (1-1000)
        offset: Number of logs to skip for pagination
        user_role: Filter logs by user role (patient, physician, admin)
        event_type: Filter logs by event type
        start_date: Filter logs from this date (ISO format)
        end_date: Filter logs until this date (ISO format)
        current_user: Current authenticated admin user
        
    Returns:
        Dict containing audit logs and metadata
    """
    # Check admin authorization
    current_user = await require_admin(request)
    
    try:
        db = get_database()
        
        # Build filter conditions
        filters = []
        params = []
        
        if user_role:
            try:
                # Validate user role
                UserRole(user_role.lower())
                filters.append("user_role = ?")
                params.append(user_role.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid user role: {user_role}"
                )
        
        if event_type:
            filters.append("event_type = ?")
            params.append(event_type)
        
        if start_date:
            try:
                datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                filters.append("timestamp >= ?")
                params.append(start_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
        
        if end_date:
            try:
                datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                filters.append("timestamp <= ?")
                params.append(end_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
        
        # Build query
        base_query = "SELECT * FROM audit_logs"
        count_query = "SELECT COUNT(*) as total FROM audit_logs"
        
        if filters:
            filter_clause = " WHERE " + " AND ".join(filters)
            base_query += filter_clause
            count_query += filter_clause
        
        base_query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute queries
        with db.get_connection() as conn:
            # Get total count
            count_cursor = conn.execute(count_query, params[:-2] if filters else [])
            total_count = count_cursor.fetchone()["total"]
            
            # Get logs
            logs_cursor = conn.execute(base_query, params)
            logs = [dict(row) for row in logs_cursor.fetchall()]
        
        # Log admin access
        logger.info(f"Admin {current_user['user_id']} accessed audit logs: "
                   f"limit={limit}, offset={offset}, filters={len(filters)}")
        
        return {
            "audit_logs": logs,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "filters_applied": {
                "user_role": user_role,
                "event_type": event_type,
                "start_date": start_date,
                "end_date": end_date
            },
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "retrieved_by": current_user["user_id"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving audit logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit logs"
        )


@router.get("/security-events", summary="Get Security Events", description="Retrieve security events and threats (Admin only)")
async def get_security_events(
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of events to retrieve"),
    offset: int = Query(default=0, ge=0, description="Number of events to skip"),
    threat_type: Optional[str] = Query(default=None, description="Filter by threat type"),
    min_risk_score: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Minimum risk score"),
    start_date: Optional[str] = Query(default=None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(default=None, description="End date (ISO format)")
):
    """
    Retrieve security events with filtering and pagination.
    
    This endpoint is restricted to admin users only and provides access to
    security events, threats, and blocked content attempts.
    
    Args:
        limit: Maximum number of events to return (1-1000)
        offset: Number of events to skip for pagination
        threat_type: Filter events by threat type
        min_risk_score: Filter events with risk score >= this value
        start_date: Filter events from this date (ISO format)
        end_date: Filter events until this date (ISO format)
        current_user: Current authenticated admin user
        
    Returns:
        Dict containing security events and metadata
    """
    # Check admin authorization
    current_user = await require_admin(request)
    
    try:
        db = get_database()
        
        # Build filter conditions
        filters = []
        params = []
        
        if threat_type:
            filters.append("threat_type = ?")
            params.append(threat_type)
        
        if min_risk_score is not None:
            filters.append("risk_score >= ?")
            params.append(min_risk_score)
        
        if start_date:
            try:
                datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                filters.append("timestamp >= ?")
                params.append(start_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
        
        if end_date:
            try:
                datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                filters.append("timestamp <= ?")
                params.append(end_date)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
                )
        
        # Build query
        base_query = "SELECT * FROM security_logs"
        count_query = "SELECT COUNT(*) as total FROM security_logs"
        
        if filters:
            filter_clause = " WHERE " + " AND ".join(filters)
            base_query += filter_clause
            count_query += filter_clause
        
        base_query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        # Execute queries
        with db.get_connection() as conn:
            # Get total count
            count_cursor = conn.execute(count_query, params[:-2] if filters else [])
            total_count = count_cursor.fetchone()["total"]
            
            # Get events
            events_cursor = conn.execute(base_query, params)
            events = [dict(row) for row in events_cursor.fetchall()]
        
        # Calculate threat statistics
        threat_stats = {}
        risk_distribution = {"low": 0, "medium": 0, "high": 0}
        
        for event in events:
            # Count by threat type
            threat_type_val = event.get("threat_type", "unknown")
            threat_stats[threat_type_val] = threat_stats.get(threat_type_val, 0) + 1
            
            # Risk score distribution
            risk_score = event.get("risk_score", 0.0)
            if risk_score < 0.3:
                risk_distribution["low"] += 1
            elif risk_score < 0.7:
                risk_distribution["medium"] += 1
            else:
                risk_distribution["high"] += 1
        
        # Log admin access
        logger.info(f"Admin {current_user['user_id']} accessed security events: "
                   f"limit={limit}, offset={offset}, filters={len(filters)}")
        
        return {
            "security_events": events,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            },
            "statistics": {
                "threat_types": threat_stats,
                "risk_distribution": risk_distribution,
                "total_events": len(events)
            },
            "filters_applied": {
                "threat_type": threat_type,
                "min_risk_score": min_risk_score,
                "start_date": start_date,
                "end_date": end_date
            },
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "retrieved_by": current_user["user_id"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving security events: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve security events"
        )


@router.get("/system-status", summary="System Status", description="Get detailed system status and configuration (Admin only)")
async def get_system_status(
    request: Request
):
    """
    Get comprehensive system status and configuration information.
    
    This endpoint provides detailed system information including:
    - Configuration status
    - Component health
    - Performance metrics
    - Security status
    
    Args:
        current_user: Current authenticated admin user
        
    Returns:
        Dict containing comprehensive system status
    """
    # Check admin authorization
    current_user = await require_admin(request)
    
    try:
        db = get_database()
        
        # Get system metrics
        metrics = db.get_metrics(days=1)
        
        # Get configuration status
        config_status = {}
        try:
            config = get_app_config()
            if config:
                config_status = {
                    "loaded": True,
                    "environment": config.environment.value,
                    "llm_provider": config.llm.provider.value,
                    "default_model": config.llm.default_model,
                    "security_features": {
                        "pii_redaction": config.security.enable_pii_redaction,
                        "guardrails": config.security.enable_guardrails,
                        "medical_disclaimers": config.security.enable_medical_disclaimers
                    },
                    "cost_tracking": {
                        "enabled": config.cost.enable_cost_tracking,
                        "daily_limit": config.cost.daily_limit,
                        "cache_enabled": config.cost.enable_response_cache,
                        "cache_ttl_hours": config.cost.cache_ttl_hours
                    }
                }
            else:
                config_status = {"loaded": False, "error": "Configuration not available"}
        except Exception as e:
            config_status = {"loaded": False, "error": str(e)}
        
        # Get component status
        component_status = {}
        
        # Database status
        try:
            with db.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) as count FROM audit_logs")
                audit_count = cursor.fetchone()["count"]
                cursor = conn.execute("SELECT COUNT(*) as count FROM security_logs")
                security_count = cursor.fetchone()["count"]
            
            component_status["database"] = {
                "status": "healthy",
                "audit_logs_count": audit_count,
                "security_logs_count": security_count
            }
        except Exception as e:
            component_status["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # LLM Gateway status
        if llm_gateway:
            try:
                gateway_health = await llm_gateway.health_check()
                component_status["llm_gateway"] = {
                    "status": "healthy",
                    "details": gateway_health
                }
            except Exception as e:
                component_status["llm_gateway"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            component_status["llm_gateway"] = {
                "status": "not_initialized"
            }
        
        # Security pipeline status
        component_status["security_pipeline"] = {
            "pii_redaction": "active",
            "guardrails": "active",
            "medical_safety": "active",
            "rate_limiting": "active",
            "audit_logging": "active"
        }
        
        # Performance metrics
        performance_metrics = {
            "queries_today": metrics.get("queries_today", 0),
            "avg_latency_ms": metrics.get("avg_latency_ms", 0),
            "total_cost_usd": metrics.get("total_cost_usd", 0.0),
            "security_events_today": metrics.get("security_events_today", 0),
            "cache_hit_rate": metrics.get("cache_hit_rate", 0.0)
        }
        
        # Log admin access
        logger.info(f"Admin {current_user['user_id']} accessed system status")
        
        return {
            "system_status": {
                "overall": "healthy",  # This would be calculated based on components
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime": "N/A"  # Would need to track application start time
            },
            "configuration": config_status,
            "components": component_status,
            "performance": performance_metrics,
            "security": {
                "events_today": metrics.get("security_events_today", 0),
                "pipeline_status": "active",
                "last_security_scan": "N/A"  # Would be implemented with actual security scanning
            },
            "metadata": {
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "retrieved_by": current_user["user_id"]
            }
        }
        
    except Exception as e:
        logger.error(f"Error retrieving system status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system status"
        )


@router.get("/user-roles-demo", summary="User Roles Demo", description="Demonstrate different user role capabilities")
async def user_roles_demo(
    request: Request
):
    """
    Demonstrate how different user roles affect API responses.
    
    This endpoint shows role-based differences in:
    - Available features
    - Rate limits
    - Model access
    - Cost limits
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Dict showing role-specific capabilities and restrictions
    """
    # Get current user (no admin requirement for this demo endpoint)
    current_user = await get_current_user(request)
    
    from ..auth.rbac import RBACService
    
    rbac_service = RBACService()
    current_role = UserRole(current_user["user_role"])
    
    # Get current user's capabilities
    current_capabilities = rbac_service.get_role_summary(current_role)
    
    # Show what this role can access
    role_demo = {
        "current_user": {
            "user_id": current_user["user_id"],
            "role": current_role.value,
            "capabilities": current_capabilities
        },
        "role_based_features": {
            "can_access_basic_chat": rbac_service.authorize_feature(current_role, "basic_chat"),
            "can_access_advanced_chat": rbac_service.authorize_feature(current_role, "advanced_chat"),
            "can_access_diagnosis_support": rbac_service.authorize_feature(current_role, "diagnosis_support"),
            "can_access_metrics": rbac_service.authorize_feature(current_role, "metrics_access"),
            "can_access_audit_logs": rbac_service.authorize_feature(current_role, "audit_logs"),
            "can_access_admin_features": rbac_service.authorize_feature(current_role, "system_configuration")
        },
        "model_access": {
            "can_use_gpt35": rbac_service.authorize_model(current_role, "gpt-3.5-turbo"),
            "can_use_gpt4": rbac_service.authorize_model(current_role, "gpt-4"),
            "allowed_models": rbac_service.get_allowed_models(current_role)
        },
        "limits": {
            "max_queries_per_hour": rbac_service.get_max_queries_per_hour(current_role),
            "max_tokens_per_query": rbac_service.get_max_tokens_per_query(current_role),
            "cost_limit_per_hour": rbac_service.get_cost_limit_per_hour(current_role)
        }
    }
    
    # If admin, show comparison with other roles
    if current_role == UserRole.ADMIN:
        role_demo["all_roles_comparison"] = rbac_service.compare_roles()
        role_demo["admin_note"] = "As an admin, you can see capabilities for all roles"
    else:
        role_demo["note"] = f"You are viewing capabilities for {current_role.value} role only"
    
    return role_demo