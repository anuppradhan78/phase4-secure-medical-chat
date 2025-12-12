"""
Demonstration of Role-Based Access Control (RBAC) system.
Shows JWT token generation, role-based permissions, rate limiting, and session management.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any

# Add src to path for imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.auth import JWTHandler, RBACService, RateLimiter, SessionManager
from src.models import UserRole


class RBACDemo:
    """Demonstration class for RBAC functionality."""
    
    def __init__(self):
        self.jwt_handler = JWTHandler()
        self.rbac_service = RBACService()
        self.rate_limiter = RateLimiter()
        self.session_manager = SessionManager()
    
    def print_section(self, title: str):
        """Print a formatted section header."""
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")
    
    def print_json(self, data: Dict[str, Any], title: str = ""):
        """Print JSON data in a formatted way."""
        if title:
            print(f"\n{title}:")
        print(json.dumps(data, indent=2, default=str))
    
    def demo_jwt_tokens(self):
        """Demonstrate JWT token generation and validation."""
        self.print_section("JWT Token Generation and Validation")
        
        # Create tokens for each role
        tokens = {}
        for role in UserRole:
            user_id = f"demo_{role.value}_user"
            token = self.jwt_handler.create_access_token(user_id, role)
            tokens[role.value] = {
                "user_id": user_id,
                "token": token,
                "role": role.value
            }
            print(f"\n{role.value.upper()} Token Created:")
            print(f"  User ID: {user_id}")
            print(f"  Token: {token[:50]}...")
        
        # Validate tokens
        print(f"\n{'Token Validation:'}")
        for role_name, token_info in tokens.items():
            user_info = self.jwt_handler.get_user_from_token(token_info["token"])
            print(f"  {role_name}: {'✓ Valid' if user_info else '✗ Invalid'}")
            if user_info:
                print(f"    User ID: {user_info['user_id']}")
                print(f"    Role: {user_info['user_role']}")
        
        return tokens
    
    def demo_role_permissions(self):
        """Demonstrate role-based permissions."""
        self.print_section("Role-Based Permissions")
        
        # Show role configurations
        print("Role Configurations:")
        role_comparison = self.rbac_service.compare_roles()
        self.print_json(role_comparison)
        
        # Test feature access
        features_to_test = [
            "basic_chat", "advanced_chat", "diagnosis_support", 
            "metrics_access", "audit_logs", "user_management"
        ]
        
        print(f"\nFeature Access Matrix:")
        print(f"{'Feature':<20} {'Patient':<10} {'Physician':<12} {'Admin':<10}")
        print("-" * 55)
        
        for feature in features_to_test:
            access = {}
            for role in UserRole:
                access[role.value] = "✓" if self.rbac_service.authorize_feature(role, feature) else "✗"
            
            print(f"{feature:<20} {access['patient']:<10} {access['physician']:<12} {access['admin']:<10}")
        
        # Test model access
        models_to_test = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
        
        print(f"\nModel Access Matrix:")
        print(f"{'Model':<15} {'Patient':<10} {'Physician':<12} {'Admin':<10}")
        print("-" * 50)
        
        for model in models_to_test:
            access = {}
            for role in UserRole:
                access[role.value] = "✓" if self.rbac_service.authorize_model(role, model) else "✗"
            
            print(f"{model:<15} {access['patient']:<10} {access['physician']:<12} {access['admin']:<10}")
    
    def demo_rate_limiting(self):
        """Demonstrate rate limiting functionality."""
        self.print_section("Rate Limiting Demonstration")
        
        # Show rate limits for all roles
        limits = self.rate_limiter.get_all_limits()
        print("Rate Limits by Role:")
        self.print_json(limits)
        
        # Simulate requests for each role
        print(f"\nSimulating Requests:")
        
        for role in UserRole:
            user_id = f"demo_{role.value}_user"
            print(f"\n{role.value.upper()} User ({user_id}):")
            
            # Check initial status
            allowed, info = self.rate_limiter.check_rate_limit(user_id, role)
            print(f"  Initial status: {info['current_requests']}/{info['limit']} requests")
            
            # Simulate some requests
            requests_to_make = min(5, info['limit'] + 2)  # Make a few requests, possibly exceeding limit
            
            for i in range(requests_to_make):
                allowed, info = self.rate_limiter.check_rate_limit(user_id, role)
                if allowed:
                    self.rate_limiter.record_request(user_id, cost=0.01)  # Small cost
                    print(f"  Request {i+1}: ✓ Allowed ({info['current_requests']}/{info['limit']})")
                else:
                    print(f"  Request {i+1}: ✗ Rate limit exceeded ({info['current_requests']}/{info['limit']})")
                    break
            
            # Show final stats
            stats = self.rate_limiter.get_user_stats(user_id, role)
            print(f"  Final stats:")
            print(f"    Requests: {stats['requests']['current']}/{stats['requests']['limit']}")
            print(f"    Cost: ${stats['cost']['current']:.4f}/${stats['cost']['limit']:.2f}")
    
    def demo_session_management(self):
        """Demonstrate session management."""
        self.print_section("Session Management")
        
        # Create sessions for each role
        sessions = {}
        for role in UserRole:
            user_id = f"demo_{role.value}_user"
            session = self.session_manager.create_session(user_id, role)
            sessions[role.value] = session
            
            print(f"\n{role.value.upper()} Session Created:")
            print(f"  Session ID: {session.session_id}")
            print(f"  User ID: {session.user_id}")
            print(f"  Created: {session.created_at}")
            print(f"  Expires: {session.expires_at}")
        
        # Simulate session activity
        print(f"\nSimulating Session Activity:")
        
        for role_name, session in sessions.items():
            print(f"\n{role_name.upper()} Session Activity:")
            
            # Update session with some activity
            for i in range(3):
                success = self.session_manager.update_session_activity(
                    session.session_id, 
                    cost=0.05,
                    metadata={"request_type": f"chat_{i+1}"}
                )
                print(f"  Activity {i+1}: {'✓' if success else '✗'}")
            
            # Get updated session
            updated_session = self.session_manager.get_session(session.session_id)
            if updated_session:
                print(f"  Total requests: {updated_session.request_count}")
                print(f"  Total cost: ${updated_session.total_cost_usd:.4f}")
                print(f"  Last activity: {updated_session.last_activity}")
        
        # Show session statistics
        stats = self.session_manager.get_session_stats()
        print(f"\nSession Statistics:")
        self.print_json(stats)
    
    def demo_access_control_scenarios(self):
        """Demonstrate different access control scenarios."""
        self.print_section("Access Control Scenarios")
        
        scenarios = [
            {
                "name": "Patient accessing basic chat",
                "role": UserRole.PATIENT,
                "feature": "basic_chat",
                "model": "gpt-3.5-turbo"
            },
            {
                "name": "Patient trying to access admin features",
                "role": UserRole.PATIENT,
                "feature": "audit_logs",
                "model": "gpt-4"
            },
            {
                "name": "Physician accessing diagnosis support",
                "role": UserRole.PHYSICIAN,
                "feature": "diagnosis_support",
                "model": "gpt-4"
            },
            {
                "name": "Admin accessing all features",
                "role": UserRole.ADMIN,
                "feature": "user_management",
                "model": "gpt-4-turbo"
            }
        ]
        
        for scenario in scenarios:
            print(f"\nScenario: {scenario['name']}")
            
            # Check feature access
            feature_allowed = self.rbac_service.authorize_feature(scenario['role'], scenario['feature'])
            print(f"  Feature '{scenario['feature']}': {'✓ Allowed' if feature_allowed else '✗ Denied'}")
            
            # Check model access
            model_allowed = self.rbac_service.authorize_model(scenario['role'], scenario['model'])
            print(f"  Model '{scenario['model']}': {'✓ Allowed' if model_allowed else '✗ Denied'}")
            
            # Get role limits
            role_config = self.rbac_service.get_role_config(scenario['role'])
            if role_config:
                print(f"  Max queries/hour: {role_config.max_queries_per_hour}")
                print(f"  Max tokens/query: {role_config.max_tokens_per_query}")
                print(f"  Cost limit/hour: ${role_config.cost_limit_per_hour:.2f}")
    
    def run_full_demo(self):
        """Run the complete RBAC demonstration."""
        print("🔐 Secure Medical Chat - RBAC System Demonstration")
        print(f"Started at: {datetime.now(timezone.utc)}")
        
        # Run all demonstrations
        tokens = self.demo_jwt_tokens()
        self.demo_role_permissions()
        self.demo_rate_limiting()
        self.demo_session_management()
        self.demo_access_control_scenarios()
        
        self.print_section("Demo Complete")
        print("✅ All RBAC components demonstrated successfully!")
        print("\nKey Features Shown:")
        print("  • JWT token generation and validation")
        print("  • Role-based feature and model access control")
        print("  • Rate limiting per user role")
        print("  • Session management with expiration")
        print("  • Different access levels for patient/physician/admin")
        
        return tokens


def main():
    """Run the RBAC demonstration."""
    demo = RBACDemo()
    tokens = demo.run_full_demo()
    
    # Save demo tokens for testing
    print(f"\n💡 Demo tokens saved for API testing:")
    for role, token_info in tokens.items():
        print(f"  {role}: {token_info['token'][:50]}...")


if __name__ == "__main__":
    main()