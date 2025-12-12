"""
Authentication and authorization module for Secure Medical Chat.
Provides JWT token management, RBAC, rate limiting, and session management.
"""

from .jwt_handler import JWTHandler
from .rbac import RBACService, RoleConfig
from .rate_limiter import RateLimiter
from .session_manager import SessionManager
from .dependencies import (
    get_current_user, require_role, require_any_role, 
    check_rate_limit, require_feature, require_admin,
    require_physician, require_patient, require_medical_staff
)
from .endpoints import router as auth_router

__all__ = [
    "JWTHandler",
    "RBACService", 
    "RoleConfig",
    "RateLimiter",
    "SessionManager",
    "get_current_user",
    "require_role",
    "require_any_role",
    "check_rate_limit",
    "require_feature",
    "require_admin",
    "require_physician", 
    "require_patient",
    "require_medical_staff",
    "auth_router"
]