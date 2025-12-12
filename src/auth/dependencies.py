"""
FastAPI dependencies for authentication and authorization.
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .jwt_handler import JWTHandler
from .rbac import RBACService
from .rate_limiter import RateLimiter
from .session_manager import SessionManager
from ..models import UserRole, UserSession


# Global instances (in production, these would be dependency-injected)
jwt_handler = JWTHandler()
rbac_service = RBACService()
rate_limiter = RateLimiter()
session_manager = SessionManager()

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, str]:
    """
    Dependency to get current authenticated user from JWT token.
    
    Returns:
        Dictionary with user_id and user_role
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_info = jwt_handler.get_user_from_token(credentials.credentials)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info


async def get_current_session(
    user_info: Dict[str, str] = Depends(get_current_user),
    session_id: Optional[str] = Header(None, alias="X-Session-ID")
) -> Optional[UserSession]:
    """
    Dependency to get current user session.
    
    Args:
        user_info: Current user information from JWT
        session_id: Session ID from header
        
    Returns:
        UserSession object or None if no session
    """
    if not session_id:
        return None
    
    session = session_manager.validate_session(session_id)
    if session and session.user_id == user_info["user_id"]:
        return session
    
    return None


def require_role(required_role: UserRole):
    """
    Dependency factory to require a specific role.
    
    Args:
        required_role: Required user role
        
    Returns:
        Dependency function
    """
    async def role_dependency(user_info: Dict[str, str] = Depends(get_current_user)) -> Dict[str, str]:
        user_role = UserRole(user_info["user_role"])
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role.value}"
            )
        return user_info
    
    return role_dependency


def require_any_role(*allowed_roles: UserRole):
    """
    Dependency factory to require any of the specified roles.
    
    Args:
        allowed_roles: Allowed user roles
        
    Returns:
        Dependency function
    """
    async def role_dependency(user_info: Dict[str, str] = Depends(get_current_user)) -> Dict[str, str]:
        user_role = UserRole(user_info["user_role"])
        if user_role not in allowed_roles:
            allowed_role_names = [role.value for role in allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_role_names)}"
            )
        return user_info
    
    return role_dependency


async def check_rate_limit(
    user_info: Dict[str, str] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Dependency to check rate limits for the current user.
    
    Args:
        user_info: Current user information
        
    Returns:
        User info if within limits
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    user_id = user_info["user_id"]
    user_role = UserRole(user_info["user_role"])
    
    allowed, info = rate_limiter.check_rate_limit(user_id, user_role)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": "Rate limit exceeded",
                "current_requests": info["current_requests"],
                "limit": info["limit"],
                "reset_time": info["reset_time"].isoformat()
            }
        )
    
    return user_info


def require_feature(feature_name: str):
    """
    Dependency factory to require access to a specific feature.
    
    Args:
        feature_name: Name of the required feature
        
    Returns:
        Dependency function
    """
    async def feature_dependency(user_info: Dict[str, str] = Depends(get_current_user)) -> Dict[str, str]:
        user_role = UserRole(user_info["user_role"])
        if not rbac_service.authorize_feature(user_role, feature_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Feature '{feature_name}' not available for role '{user_role.value}'"
            )
        return user_info
    
    return feature_dependency


async def get_rbac_service() -> RBACService:
    """Dependency to get RBAC service."""
    return rbac_service


async def get_rate_limiter() -> RateLimiter:
    """Dependency to get rate limiter."""
    return rate_limiter


async def get_session_manager() -> SessionManager:
    """Dependency to get session manager."""
    return session_manager


async def get_jwt_handler() -> JWTHandler:
    """Dependency to get JWT handler."""
    return jwt_handler


# Convenience dependencies for common role requirements
require_admin = require_role(UserRole.ADMIN)
require_physician = require_role(UserRole.PHYSICIAN)
require_patient = require_role(UserRole.PATIENT)

# Common role combinations
require_medical_staff = require_any_role(UserRole.PHYSICIAN, UserRole.ADMIN)
require_authenticated = get_current_user