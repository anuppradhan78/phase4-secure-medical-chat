"""
Unit tests for Role-Based Access Control (RBAC) components.
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

# Add src to path for imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.auth import JWTHandler, RBACService, RateLimiter, SessionManager
from src.models import UserRole


class TestJWTHandler:
    """Test JWT token generation and validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.jwt_handler = JWTHandler()
    
    def test_create_access_token(self):
        """Test JWT token creation."""
        user_id = "test_user"
        user_role = UserRole.PATIENT
        
        token = self.jwt_handler.create_access_token(user_id, user_role)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self):
        """Test verification of valid token."""
        user_id = "test_user"
        user_role = UserRole.PHYSICIAN
        
        token = self.jwt_handler.create_access_token(user_id, user_role)
        payload = self.jwt_handler.verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["role"] == user_role.value
    
    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        invalid_token = "invalid.token.here"
        payload = self.jwt_handler.verify_token(invalid_token)
        
        assert payload is None
    
    def test_get_user_from_token(self):
        """Test extracting user info from token."""
        user_id = "test_admin"
        user_role = UserRole.ADMIN
        
        token = self.jwt_handler.create_access_token(user_id, user_role)
        user_info = self.jwt_handler.get_user_from_token(token)
        
        assert user_info is not None
        assert user_info["user_id"] == user_id
        assert user_info["user_role"] == user_role.value
    
    def test_create_demo_token(self):
        """Test demo token creation."""
        user_role = UserRole.PATIENT
        token = self.jwt_handler.create_demo_token(user_role)
        
        user_info = self.jwt_handler.get_user_from_token(token)
        assert user_info is not None
        assert user_info["user_role"] == user_role.value
        assert "demo_patient_user" in user_info["user_id"]


class TestRBACService:
    """Test Role-Based Access Control service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rbac_service = RBACService()
    
    def test_get_role_config(self):
        """Test getting role configuration."""
        patient_config = self.rbac_service.get_role_config(UserRole.PATIENT)
        physician_config = self.rbac_service.get_role_config(UserRole.PHYSICIAN)
        admin_config = self.rbac_service.get_role_config(UserRole.ADMIN)
        
        assert patient_config is not None
        assert patient_config.max_queries_per_hour == 10
        assert "gpt-3.5-turbo" in patient_config.allowed_models
        
        assert physician_config is not None
        assert physician_config.max_queries_per_hour == 100
        assert "gpt-4" in physician_config.allowed_models
        
        assert admin_config is not None
        assert admin_config.max_queries_per_hour == 1000
        assert "all" in admin_config.features
    
    def test_authorize_feature(self):
        """Test feature authorization."""
        # Patient should have basic features
        assert self.rbac_service.authorize_feature(UserRole.PATIENT, "basic_chat")
        assert not self.rbac_service.authorize_feature(UserRole.PATIENT, "audit_logs")
        
        # Physician should have advanced features
        assert self.rbac_service.authorize_feature(UserRole.PHYSICIAN, "diagnosis_support")
        assert not self.rbac_service.authorize_feature(UserRole.PHYSICIAN, "user_management")
        
        # Admin should have all features
        assert self.rbac_service.authorize_feature(UserRole.ADMIN, "audit_logs")
        assert self.rbac_service.authorize_feature(UserRole.ADMIN, "user_management")
        assert self.rbac_service.authorize_feature(UserRole.ADMIN, "basic_chat")
    
    def test_authorize_model(self):
        """Test model authorization."""
        # Patient should only access basic models
        assert self.rbac_service.authorize_model(UserRole.PATIENT, "gpt-3.5-turbo")
        assert not self.rbac_service.authorize_model(UserRole.PATIENT, "gpt-4")
        
        # Physician should access advanced models
        assert self.rbac_service.authorize_model(UserRole.PHYSICIAN, "gpt-3.5-turbo")
        assert self.rbac_service.authorize_model(UserRole.PHYSICIAN, "gpt-4")
        
        # Admin should access all models
        assert self.rbac_service.authorize_model(UserRole.ADMIN, "gpt-4-turbo")
    
    def test_validate_request_limits(self):
        """Test request limit validation."""
        # Test within limits
        result = self.rbac_service.validate_request_limits(
            UserRole.PATIENT, token_count=400, estimated_cost=0.5
        )
        assert result["valid"] is True
        assert result["token_limit_ok"] is True
        assert result["cost_limit_ok"] is True
        
        # Test exceeding token limit
        result = self.rbac_service.validate_request_limits(
            UserRole.PATIENT, token_count=600, estimated_cost=0.5
        )
        assert result["valid"] is False
        assert result["token_limit_ok"] is False
        
        # Test exceeding cost limit
        result = self.rbac_service.validate_request_limits(
            UserRole.PATIENT, token_count=400, estimated_cost=2.0
        )
        assert result["valid"] is False
        assert result["cost_limit_ok"] is False


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rate_limiter = RateLimiter()
    
    def test_check_rate_limit_within_limits(self):
        """Test rate limit check when within limits."""
        user_id = "test_user"
        user_role = UserRole.PATIENT
        
        allowed, info = self.rate_limiter.check_rate_limit(user_id, user_role)
        
        assert allowed is True
        assert info["current_requests"] == 0
        assert info["limit"] == 10  # Patient limit
        assert info["remaining"] == 10
    
    def test_rate_limit_enforcement(self):
        """Test rate limit enforcement."""
        user_id = "test_patient"
        user_role = UserRole.PATIENT
        
        # Make requests up to the limit
        for i in range(10):  # Patient limit is 10
            allowed, info = self.rate_limiter.check_rate_limit(user_id, user_role)
            if allowed:
                self.rate_limiter.record_request(user_id)
        
        # Next request should be blocked
        allowed, info = self.rate_limiter.check_rate_limit(user_id, user_role)
        assert allowed is False
        assert info["current_requests"] == 10
        assert info["remaining"] == 0
    
    def test_cost_limit_enforcement(self):
        """Test cost limit enforcement."""
        user_id = "test_patient"
        user_role = UserRole.PATIENT
        
        # Test within cost limit
        allowed, info = self.rate_limiter.check_cost_limit(user_id, user_role, 0.5)
        assert allowed is True
        
        # Test exceeding cost limit
        allowed, info = self.rate_limiter.check_cost_limit(user_id, user_role, 2.0)
        assert allowed is False
        assert info["total_cost"] == 2.0
        assert info["limit"] == 1.0  # Patient cost limit
    
    def test_different_role_limits(self):
        """Test different limits for different roles."""
        patient_allowed, patient_info = self.rate_limiter.check_rate_limit("patient_user", UserRole.PATIENT)
        physician_allowed, physician_info = self.rate_limiter.check_rate_limit("physician_user", UserRole.PHYSICIAN)
        admin_allowed, admin_info = self.rate_limiter.check_rate_limit("admin_user", UserRole.ADMIN)
        
        assert patient_info["limit"] == 10
        assert physician_info["limit"] == 100
        assert admin_info["limit"] == 1000
    
    def test_user_stats(self):
        """Test user statistics."""
        user_id = "stats_user"
        user_role = UserRole.PHYSICIAN
        
        # Record some requests
        for i in range(5):
            self.rate_limiter.record_request(user_id, cost=0.1)
        
        stats = self.rate_limiter.get_user_stats(user_id, user_role)
        
        assert stats["user_id"] == user_id
        assert stats["user_role"] == user_role.value
        assert stats["requests"]["current"] == 5
        assert stats["requests"]["limit"] == 100
        assert stats["cost"]["current"] == 0.5


class TestSessionManager:
    """Test session management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session_manager = SessionManager()
    
    def test_create_session(self):
        """Test session creation."""
        user_id = "test_user"
        user_role = UserRole.PATIENT
        
        session = self.session_manager.create_session(user_id, user_role)
        
        assert session.user_id == user_id
        assert session.user_role == user_role
        assert session.is_active is True
        assert session.request_count == 0
        assert session.total_cost_usd == 0.0
        assert len(session.session_id) > 0
    
    def test_get_session(self):
        """Test getting a session."""
        user_id = "test_user"
        user_role = UserRole.PHYSICIAN
        
        created_session = self.session_manager.create_session(user_id, user_role)
        retrieved_session = self.session_manager.get_session(created_session.session_id)
        
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id
        assert retrieved_session.user_id == user_id
    
    def test_validate_session(self):
        """Test session validation and activity update."""
        user_id = "test_user"
        user_role = UserRole.ADMIN
        
        session = self.session_manager.create_session(user_id, user_role)
        original_activity = session.last_activity
        
        # Small delay to ensure timestamp difference
        time.sleep(0.01)
        
        validated_session = self.session_manager.validate_session(session.session_id)
        
        assert validated_session is not None
        assert validated_session.last_activity > original_activity
    
    def test_update_session_activity(self):
        """Test updating session activity."""
        user_id = "test_user"
        user_role = UserRole.PATIENT
        
        session = self.session_manager.create_session(user_id, user_role)
        
        success = self.session_manager.update_session_activity(
            session.session_id, 
            cost=0.05,
            metadata={"test": "data"}
        )
        
        assert success is True
        
        updated_session = self.session_manager.get_session(session.session_id)
        assert updated_session.request_count == 1
        assert updated_session.total_cost_usd == 0.05
        assert updated_session.metadata["test"] == "data"
    
    def test_deactivate_session(self):
        """Test session deactivation."""
        user_id = "test_user"
        user_role = UserRole.PHYSICIAN
        
        session = self.session_manager.create_session(user_id, user_role)
        
        success = self.session_manager.deactivate_session(session.session_id)
        assert success is True
        
        deactivated_session = self.session_manager.get_session(session.session_id)
        assert deactivated_session is None  # Should return None for inactive session
    
    def test_get_user_sessions(self):
        """Test getting all sessions for a user."""
        user_id = "multi_session_user"
        user_role = UserRole.ADMIN
        
        # Create multiple sessions
        session1 = self.session_manager.create_session(user_id, user_role)
        session2 = self.session_manager.create_session(user_id, user_role)
        
        user_sessions = self.session_manager.get_user_sessions(user_id)
        
        assert len(user_sessions) == 2
        session_ids = [s.session_id for s in user_sessions]
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids
    
    def test_revoke_user_sessions(self):
        """Test revoking all sessions for a user."""
        user_id = "revoke_test_user"
        user_role = UserRole.PATIENT
        
        # Create multiple sessions
        self.session_manager.create_session(user_id, user_role)
        self.session_manager.create_session(user_id, user_role)
        
        revoked_count = self.session_manager.revoke_user_sessions(user_id)
        
        assert revoked_count == 2
        
        remaining_sessions = self.session_manager.get_user_sessions(user_id)
        assert len(remaining_sessions) == 0
    
    def test_session_stats(self):
        """Test session statistics."""
        # Create sessions with different roles
        self.session_manager.create_session("user1", UserRole.PATIENT)
        self.session_manager.create_session("user2", UserRole.PHYSICIAN)
        self.session_manager.create_session("user3", UserRole.ADMIN)
        
        stats = self.session_manager.get_session_stats()
        
        assert stats["total_sessions"] >= 3
        assert stats["active_sessions"] >= 3
        assert "patient" in stats["sessions_by_role"]
        assert "physician" in stats["sessions_by_role"]
        assert "admin" in stats["sessions_by_role"]
    
    def test_create_demo_session(self):
        """Test demo session creation."""
        user_role = UserRole.PHYSICIAN
        
        session = self.session_manager.create_demo_session(user_role)
        
        assert session.user_role == user_role
        assert "demo_physician" in session.user_id
        assert session.is_active is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])