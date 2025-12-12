"""
Simple API integration test for RBAC endpoints.
"""

import sys
sys.path.append('src')

from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.auth.endpoints import router as auth_router

# Create FastAPI app
app = FastAPI(title="Secure Medical Chat - RBAC Demo")
app.include_router(auth_router)

# Create test client
client = TestClient(app)

def test_auth_endpoints():
    print("🌐 Testing RBAC API Endpoints")
    print("=" * 50)
    
    # Test creating demo tokens
    print("\n1. Creating Demo Tokens:")
    tokens = {}
    
    for role in ["patient", "physician", "admin"]:
        response = client.post(f"/auth/demo/{role}-token")
        if response.status_code == 200:
            token_data = response.json()
            tokens[role] = token_data
            print(f"  ✅ {role.capitalize()}: {token_data['access_token'][:50]}...")
        else:
            print(f"  ❌ {role.capitalize()}: Failed ({response.status_code})")
    
    # Test authentication
    print("\n2. Testing Authentication:")
    for role, token_data in tokens.items():
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        response = client.get("/auth/me", headers=headers)
        
        if response.status_code == 200:
            user_info = response.json()
            print(f"  ✅ {role.capitalize()}: {user_info['user_id']} ({user_info['user_role']})")
        else:
            print(f"  ❌ {role.capitalize()}: Auth failed ({response.status_code})")
    
    # Test role-based access
    print("\n3. Testing Role-Based Access:")
    
    # Test admin-only endpoint
    print("  Admin-only endpoint (/auth/admin/sessions):")
    for role, token_data in tokens.items():
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        response = client.get("/auth/admin/sessions", headers=headers)
        
        expected = 200 if role == "admin" else 403
        status_icon = "✅" if response.status_code == expected else "❌"
        print(f"    {status_icon} {role.capitalize()}: {response.status_code} (expected {expected})")
    
    # Test rate limiting info (should work for all authenticated users)
    print("  Rate limit info (/auth/rate-limit):")
    for role, token_data in tokens.items():
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        response = client.get("/auth/rate-limit", headers=headers)
        
        if response.status_code == 200:
            limit_info = response.json()
            print(f"    ✅ {role.capitalize()}: {limit_info['requests']['current']}/{limit_info['requests']['limit']} requests")
        else:
            print(f"    ❌ {role.capitalize()}: Failed ({response.status_code})")
    
    # Test role comparison (public endpoint)
    print("\n4. Testing Public Endpoints:")
    response = client.get("/auth/roles")
    if response.status_code == 200:
        roles_data = response.json()
        print(f"  ✅ Role comparison: {len(roles_data)} roles available")
        for role_name, role_info in roles_data.items():
            print(f"    {role_name}: {role_info['max_queries_per_hour']} queries/hour")
    else:
        print(f"  ❌ Role comparison failed: {response.status_code}")
    
    print("\n✅ API Integration Test Complete!")
    return tokens

if __name__ == "__main__":
    # Install test client if not available
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        print("Installing httpx for testing...")
        import subprocess
        subprocess.run(["pip", "install", "httpx"])
        from fastapi.testclient import TestClient
    
    tokens = test_auth_endpoints()
    
    print(f"\n💡 Demo tokens for manual testing:")
    for role, token_data in tokens.items():
        print(f"  {role}: {token_data['access_token']}")
    
    print(f"\nTo start the full API server:")
    print(f"  uvicorn src.main:app --reload")