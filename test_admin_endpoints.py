#!/usr/bin/env python3
"""
Test script for admin endpoints to verify they work correctly.
"""

import asyncio
import json
from fastapi.testclient import TestClient
from src.main import app

def test_admin_endpoints():
    """Test the admin endpoints functionality."""
    client = TestClient(app)
    
    print("🧪 Testing Admin Endpoints...")
    
    # Test health endpoint (should be accessible to all)
    print("\n1. Testing /api/health endpoint...")
    response = client.get("/api/health")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        health_data = response.json()
        print(f"   Service: {health_data.get('service', 'unknown')}")
        print(f"   Overall Status: {health_data.get('overall_status', 'unknown')}")
    else:
        print(f"   Error: {response.text}")
    
    # Test admin endpoints without authentication (should fail)
    print("\n2. Testing /api/audit-logs without admin auth (should fail)...")
    response = client.get("/api/audit-logs")
    print(f"   Status: {response.status_code} (expected 401 or 403)")
    
    print("\n3. Testing /api/security-events without admin auth (should fail)...")
    response = client.get("/api/security-events")
    print(f"   Status: {response.status_code} (expected 401 or 403)")
    
    # Test admin endpoints with admin headers
    admin_headers = {
        "X-User-ID": "admin_test",
        "X-User-Role": "admin",
        "X-Session-ID": "test_session_123"
    }
    
    print("\n4. Testing /api/audit-logs with admin auth...")
    response = client.get("/api/audit-logs", headers=admin_headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total logs: {data.get('pagination', {}).get('total', 0)}")
        print(f"   Retrieved: {len(data.get('audit_logs', []))}")
    else:
        print(f"   Error: {response.text}")
    
    print("\n5. Testing /api/security-events with admin auth...")
    response = client.get("/api/security-events", headers=admin_headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Total events: {data.get('pagination', {}).get('total', 0)}")
        print(f"   Retrieved: {len(data.get('security_events', []))}")
    else:
        print(f"   Error: {response.text}")
    
    print("\n6. Testing /api/system-status with admin auth...")
    response = client.get("/api/system-status", headers=admin_headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   System Status: {data.get('system_status', {}).get('overall', 'unknown')}")
        print(f"   Configuration Loaded: {data.get('configuration', {}).get('loaded', False)}")
    else:
        print(f"   Error: {response.text}")
    
    print("\n7. Testing /api/user-roles-demo...")
    response = client.get("/api/user-roles-demo", headers=admin_headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Current Role: {data.get('current_user', {}).get('role', 'unknown')}")
        print(f"   Can Access Admin Features: {data.get('role_based_features', {}).get('can_access_admin_features', False)}")
    else:
        print(f"   Error: {response.text}")
    
    # Test with different user roles
    print("\n8. Testing role-based access with physician role...")
    physician_headers = {
        "X-User-ID": "physician_test",
        "X-User-Role": "physician",
        "X-Session-ID": "test_session_456"
    }
    
    response = client.get("/api/user-roles-demo", headers=physician_headers)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Current Role: {data.get('current_user', {}).get('role', 'unknown')}")
        print(f"   Can Access Admin Features: {data.get('role_based_features', {}).get('can_access_admin_features', False)}")
    
    # Test physician trying to access admin endpoint (should fail)
    response = client.get("/api/audit-logs", headers=physician_headers)
    print(f"   Physician accessing audit logs: {response.status_code} (expected 403)")
    
    print("\n9. Testing OpenAPI documentation...")
    response = client.get("/docs")
    print(f"   Swagger UI Status: {response.status_code}")
    
    response = client.get("/openapi.json")
    print(f"   OpenAPI Schema Status: {response.status_code}")
    if response.status_code == 200:
        openapi_data = response.json()
        print(f"   API Title: {openapi_data.get('info', {}).get('title', 'unknown')}")
        print(f"   API Version: {openapi_data.get('info', {}).get('version', 'unknown')}")
        print(f"   Number of paths: {len(openapi_data.get('paths', {}))}")
        
        # Check if admin endpoints are documented
        paths = openapi_data.get('paths', {})
        admin_endpoints = [path for path in paths.keys() if 'audit-logs' in path or 'security-events' in path]
        print(f"   Admin endpoints documented: {len(admin_endpoints)}")
    
    print("\n✅ Admin endpoints testing completed!")

if __name__ == "__main__":
    test_admin_endpoints()