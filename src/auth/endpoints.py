"""
Authentication and authorization endpoints.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import timedelta

from .dependencies import (
    get_jwt_handler, get_rbac_service, get_rate_limiter, 
    get_session_manager, get_current_user, require_admin,
    check_rate_limit
)
from .jwt_handler import JWTHandler
from .rbac import RBACService
from .rate_limiter import RateLimiter
from .session_manager import SessionManager
from ..models import UserRole, UserSession


# Request/Response models
class TokenRequest(BaseModel):
    """Request model for token generation."""
    user_role: UserRole
    user_id: Optional[str] = None
    session_duration_hours: Optional[int] = 24


class TokenResponse(BaseModel):
    """Response model for token generation."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    user_role: str
    session_id: Optional[str] = None


class SessionResponse(BaseModel):
    """Response model for session information."""
    session_id: str
    user_id: str
    user_role: str
    created_at: str
    expires_at: str
    is_active: bool
    request_count: int
    total_cost_usd: float


class RateLimitResponse(BaseModel):
    """Response model for rate limit information."""
    user_id: str
    user_role: str
    requests: Dict[str, Any]
    cost: Dict[str, Any]
    reset_time: str


# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse)
async def create_token(
    request: TokenRequest,
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    Create a JWT token for demonstration purposes.
    In production, this would require proper authentication.
    """
    # Generate user ID if not provided
    user_id = request.user_id or f"demo_{request.user_role.value}_user"
    
    # Create JWT token
    expires_delta = timedelta(hours=request.session_duration_hours)
    access_token = jwt_handler.create_access_token(
        user_id=user_id,
        user_role=request.user_role,
        expires_delta=expires_delta
    )
    
    # Create session
    session = session_manager.create_session(
        user_id=user_id,
        user_role=request.user_role,
        session_duration_hours=request.session_duration_hours
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=request.session_duration_hours * 3600,
        user_id=user_id,
        user_role=request.user_role.value,
        session_id=session.session_id
    )


@router.get("/me")
async def get_current_user_info(
    user_info: Dict[str, str] = Depends(get_current_user),
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """Get current user information and capabilities."""
    user_role = UserRole(user_info["user_role"])
    role_summary = rbac_service.get_role_summary(user_role)
    
    return {
        "user_id": user_info["user_id"],
        "user_role": user_info["user_role"],
        "capabilities": role_summary
    }


@router.get("/session", response_model=SessionResponse)
async def get_session_info(
    user_info: Dict[str, str] = Depends(get_current_user),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get current session information."""
    # Get all sessions for user
    sessions = session_manager.get_user_sessions(user_info["user_id"])
    
    if not sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found"
        )
    
    # Return the most recent session
    session = max(sessions, key=lambda s: s.last_activity)
    
    return SessionResponse(
        session_id=session.session_id,
        user_id=session.user_id,
        user_role=session.user_role.value,
        created_at=session.created_at.isoformat(),
        expires_at=session.expires_at.isoformat(),
        is_active=session.is_active,
        request_count=session.request_count,
        total_cost_usd=session.total_cost_usd
    )


@router.get("/rate-limit", response_model=RateLimitResponse)
async def get_rate_limit_info(
    user_info: Dict[str, str] = Depends(check_rate_limit),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
):
    """Get current rate limit status for the user."""
    user_id = user_info["user_id"]
    user_role = UserRole(user_info["user_role"])
    
    stats = rate_limiter.get_user_stats(user_id, user_role)
    
    return RateLimitResponse(
        user_id=stats["user_id"],
        user_role=stats["user_role"],
        requests=stats["requests"],
        cost=stats["cost"],
        reset_time=stats["reset_time"].isoformat()
    )


@router.get("/roles")
async def get_role_comparison(
    rbac_service: RBACService = Depends(get_rbac_service)
):
    """Get comparison of all user roles and their capabilities."""
    return rbac_service.compare_roles()


@router.get("/limits")
async def get_all_limits(
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
):
    """Get rate limits for all roles."""
    return rate_limiter.get_all_limits()


@router.post("/logout")
async def logout(
    user_info: Dict[str, str] = Depends(get_current_user),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Logout and revoke all user sessions."""
    revoked_count = session_manager.revoke_user_sessions(user_info["user_id"])
    
    return {
        "message": "Logged out successfully",
        "sessions_revoked": revoked_count
    }


# Admin-only endpoints
@router.get("/admin/sessions")
async def get_all_sessions(
    user_info: Dict[str, str] = Depends(require_admin),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Get statistics about all sessions (admin only)."""
    return session_manager.get_session_stats()


@router.post("/admin/cleanup")
async def cleanup_expired_sessions(
    user_info: Dict[str, str] = Depends(require_admin),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Clean up expired sessions (admin only)."""
    cleaned_count = session_manager.cleanup_expired_sessions()
    
    return {
        "message": "Cleanup completed",
        "sessions_cleaned": cleaned_count
    }


@router.post("/admin/reset-limits/{target_user_id}")
async def reset_user_limits(
    target_user_id: str,
    user_info: Dict[str, str] = Depends(require_admin),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
):
    """Reset rate limits for a specific user (admin only)."""
    rate_limiter.reset_user_limits(target_user_id)
    
    return {
        "message": f"Rate limits reset for user {target_user_id}"
    }


# Demo endpoints for testing different roles
@router.post("/demo/patient-token", response_model=TokenResponse)
async def create_patient_demo_token(
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Create a demo patient token for testing."""
    user_id = "demo_patient_001"
    access_token = jwt_handler.create_access_token(user_id, UserRole.PATIENT)
    session = session_manager.create_session(user_id, UserRole.PATIENT)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=3600,
        user_id=user_id,
        user_role=UserRole.PATIENT.value,
        session_id=session.session_id
    )


@router.post("/demo/physician-token", response_model=TokenResponse)
async def create_physician_demo_token(
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Create a demo physician token for testing."""
    user_id = "demo_physician_001"
    access_token = jwt_handler.create_access_token(user_id, UserRole.PHYSICIAN)
    session = session_manager.create_session(user_id, UserRole.PHYSICIAN)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=3600,
        user_id=user_id,
        user_role=UserRole.PHYSICIAN.value,
        session_id=session.session_id
    )


@router.post("/demo/admin-token", response_model=TokenResponse)
async def create_admin_demo_token(
    jwt_handler: JWTHandler = Depends(get_jwt_handler),
    session_manager: SessionManager = Depends(get_session_manager)
):
    """Create a demo admin token for testing."""
    user_id = "demo_admin_001"
    access_token = jwt_handler.create_access_token(user_id, UserRole.ADMIN)
    session = session_manager.create_session(user_id, UserRole.ADMIN)
    
    return TokenResponse(
        access_token=access_token,
        expires_in=3600,
        user_id=user_id,
        user_role=UserRole.ADMIN.value,
        session_id=session.session_id
    )