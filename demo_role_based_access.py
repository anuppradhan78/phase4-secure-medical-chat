#!/usr/bin/env python3
"""
Demonstration script showing how different user roles affect API responses.
"""

from fastapi.testclient import TestClient
from src.main import app
import json

def demo_role_based_access():
    """Demonstrate role-based access control across different endpoints."""
    client = TestClient(app)
    
    print("🎭 Role-Based Access Control Demonstration")
    print("=" * 60)
    
    # Define different user roles
    roles = {
        "patient": {
            "headers": {
                "X-User-ID": "patient_demo",
                "X-User-Role": "patient",
                "X-Session-ID": "patient_session_123"
            },
            "description": "Basic user with limited health information access"
        },
        "physician": {
            "headers": {
                "X-User-ID": "physician_demo", 
                "X-User-Role": "physician",
                "X-Session-ID": "physician_session_456"
            },
            "description": "Medical professional with advanced AI capabilities"
        },
        "admin": {
            "headers": {
                "X-User-ID": "admin_demo",
                "X-User-Role": "admin", 
                "X-Session-ID": "admin_session_789"
            },
            "description": "System administrator with full access"
        }
    }
    
    # Test endpoints that show role differences
    endpoints_to_test = [
        {
            "path": "/api/user-roles-demo",
            "method": "GET",
            "description": "User capabilities demo",
            "all_roles": True
        },
        {
            "path": "/api/audit-logs",
            "method": "GET", 
            "description": "Audit logs access",
            "admin_only": True
        },
        {
            "path": "/api/security-events",
            "method": "GET",
            "description": "Security events access", 
            "admin_only": True
        },
        {
            "path": "/api/system-status",
            "method": "GET",
            "description": "System status information",
            "admin_only": True
        }
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\n📍 Testing: {endpoint['path']}")
        print(f"   Description: {endpoint['description']}")
        print("-" * 50)
        
        for role_name, role_info in roles.items():
            print(f"\n👤 {role_name.upper()} Role:")
            print(f"   {role_info['description']}")
            
            if endpoint.get("method") == "GET":
                response = client.get(endpoint["path"], headers=role_info["headers"])
            else:
                response = client.post(endpoint["path"], headers=role_info["headers"])
            
            print(f"   Status: {response.status_code}", end="")
            
            if response.status_code == 200:
                print(" ✅ SUCCESS")
                data = response.json()
                
                # Show relevant information based on endpoint
                if "user-roles-demo" in endpoint["path"]:
                    current_role = data.get("current_user", {}).get("role", "unknown")
                    features = data.get("role_based_features", {})
                    print(f"   Current Role: {current_role}")
                    print(f"   Can Access Basic Chat: {features.get('can_access_basic_chat', False)}")
                    print(f"   Can Access Advanced Chat: {features.get('can_access_advanced_chat', False)}")
                    print(f"   Can Access Admin Features: {features.get('can_access_admin_features', False)}")
                    
                    limits = data.get("limits", {})
                    print(f"   Max Queries/Hour: {limits.get('max_queries_per_hour', 0)}")
                    print(f"   Max Tokens/Query: {limits.get('max_tokens_per_query', 0)}")
                    
                elif "audit-logs" in endpoint["path"]:
                    pagination = data.get("pagination", {})
                    print(f"   Total Audit Logs: {pagination.get('total', 0)}")
                    print(f"   Retrieved: {len(data.get('audit_logs', []))}")
                    
                elif "security-events" in endpoint["path"]:
                    pagination = data.get("pagination", {})
                    stats = data.get("statistics", {})
                    print(f"   Total Security Events: {pagination.get('total', 0)}")
                    print(f"   Risk Distribution: {stats.get('risk_distribution', {})}")
                    
                elif "system-status" in endpoint["path"]:
                    system_status = data.get("system_status", {})
                    performance = data.get("performance", {})
                    print(f"   System Status: {system_status.get('overall', 'unknown')}")
                    print(f"   Queries Today: {performance.get('queries_today', 0)}")
                    print(f"   Total Cost: ${performance.get('total_cost_usd', 0.0):.4f}")
                    
            elif response.status_code == 403:
                print(" ❌ FORBIDDEN - Insufficient permissions")
                error_detail = response.json().get("detail", "Access denied")
                print(f"   Reason: {error_detail}")
                
            elif response.status_code == 401:
                print(" ❌ UNAUTHORIZED - Authentication required")
                
            else:
                print(f" ❌ ERROR - {response.status_code}")
                try:
                    error_detail = response.json().get("detail", "Unknown error")
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Error: {response.text}")
    
    print("\n" + "=" * 60)
    print("🎯 Role-Based Access Summary:")
    print("   • PATIENT: Basic health info, limited queries, GPT-3.5 only")
    print("   • PHYSICIAN: Advanced medical AI, more queries, GPT-3.5 & GPT-4")
    print("   • ADMIN: Full system access, unlimited queries, all models")
    print("\n✅ Role-based access control demonstration completed!")

if __name__ == "__main__":
    demo_role_based_access()