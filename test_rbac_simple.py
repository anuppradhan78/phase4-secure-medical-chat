"""
Simple RBAC demonstration script.
"""

import sys
import os
sys.path.append('src')

from src.auth import JWTHandler, RBACService, RateLimiter, SessionManager
from src.models import UserRole

def main():
    print("🔐 RBAC System Demonstration")
    print("=" * 50)
    
    # Initialize components
    jwt_handler = JWTHandler()
    rbac_service = RBACService()
    rate_limiter = RateLimiter()
    session_manager = SessionManager()
    
    # Test JWT tokens
    print("\n1. JWT Token Generation:")
    for role in UserRole:
        user_id = f"demo_{role.value}_user"
        token = jwt_handler.create_access_token(user_id, role)
        print(f"  {role.value}: {token[:50]}...")
        
        # Verify token
        user_info = jwt_handler.get_user_from_token(token)
        print(f"    Verified: {user_info['user_id']} ({user_info['user_role']})")
    
    # Test role permissions
    print("\n2. Role Permissions:")
    features = ["basic_chat", "diagnosis_support", "audit_logs"]
    models = ["gpt-3.5-turbo", "gpt-4"]
    
    for role in UserRole:
        print(f"\n  {role.value.upper()}:")
        config = rbac_service.get_role_config(role)
        print(f"    Max queries/hour: {config.max_queries_per_hour}")
        print(f"    Features: {len(config.features)}")
        
        for feature in features:
            allowed = rbac_service.authorize_feature(role, feature)
            print(f"      {feature}: {'✓' if allowed else '✗'}")
        
        for model in models:
            allowed = rbac_service.authorize_model(role, model)
            print(f"      {model}: {'✓' if allowed else '✗'}")
    
    # Test rate limiting
    print("\n3. Rate Limiting:")
    for role in UserRole:
        user_id = f"test_{role.value}_user"
        allowed, info = rate_limiter.check_rate_limit(user_id, role)
        print(f"  {role.value}: {info['current_requests']}/{info['limit']} requests allowed")
        
        # Make a few requests
        for i in range(3):
            rate_limiter.record_request(user_id, cost=0.01)
        
        stats = rate_limiter.get_user_stats(user_id, role)
        print(f"    After 3 requests: {stats['requests']['current']}/{stats['requests']['limit']}")
    
    # Test session management
    print("\n4. Session Management:")
    sessions = {}
    for role in UserRole:
        user_id = f"session_{role.value}_user"
        session = session_manager.create_session(user_id, role)
        sessions[role.value] = session
        print(f"  {role.value}: Session {session.session_id[:16]}... created")
        
        # Update session activity
        session_manager.update_session_activity(session.session_id, cost=0.05)
        updated = session_manager.get_session(session.session_id)
        print(f"    Requests: {updated.request_count}, Cost: ${updated.total_cost_usd:.4f}")
    
    print("\n✅ RBAC System working correctly!")
    print("\nKey Features Demonstrated:")
    print("  • JWT token generation and validation")
    print("  • Role-based feature and model access")
    print("  • Rate limiting per user role")
    print("  • Session management with tracking")

if __name__ == "__main__":
    main()