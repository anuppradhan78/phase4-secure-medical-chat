"""
API demonstration of RBAC system with FastAPI endpoints.
Shows how different user roles interact with protected endpoints.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

# Demo server URL (assumes FastAPI server is running)
BASE_URL = "http://localhost:8000"


class APIRBACDemo:
    """Demonstration of RBAC through API calls."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.tokens = {}
    
    async def create_demo_tokens(self):
        """Create demo tokens for all roles."""
        print("🔑 Creating demo tokens for all roles...")
        
        roles = ["patient", "physician", "admin"]
        
        async with httpx.AsyncClient() as client:
            for role in roles:
                try:
                    response = await client.post(f"{self.base_url}/auth/demo/{role}-token")
                    if response.status_code == 200:
                        token_data = response.json()
                        self.tokens[role] = token_data
                        print(f"  ✅ {role.capitalize()} token created")
                    else:
                        print(f"  ❌ Failed to create {role} token: {response.status_code}")
                except Exception as e:
                    print(f"  ❌ Error creating {role} token: {e}")
        
        return self.tokens
    
    async def test_authentication(self):
        """Test authentication with different tokens."""
        print(f"\n🔐 Testing Authentication")
        print("-" * 40)
        
        async with httpx.AsyncClient() as client:
            for role, token_data in self.tokens.items():
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                
                try:
                    response = await client.get(f"{self.base_url}/auth/me", headers=headers)
                    if response.status_code == 200:
                        user_info = response.json()
                        print(f"  ✅ {role.capitalize()}: Authenticated as {user_info['user_id']}")
                        print(f"     Role: {user_info['user_role']}")
                        print(f"     Features: {len(user_info['capabilities']['features'])} available")
                    else:
                        print(f"  ❌ {role.capitalize()}: Authentication failed ({response.status_code})")
                except Exception as e:
                    print(f"  ❌ {role.capitalize()}: Error - {e}")
    
    async def test_role_access(self):
        """Test role-based access to different endpoints."""
        print(f"\n🚪 Testing Role-Based Access")
        print("-" * 40)
        
        # Test endpoints with different access requirements
        test_cases = [
            {
                "endpoint": "/auth/rate-limit",
                "method": "GET",
                "description": "Rate limit info (authenticated users)",
                "expected": {"patient": 200, "physician": 200, "admin": 200}
            },
            {
                "endpoint": "/auth/admin/sessions",
                "method": "GET", 
                "description": "Session stats (admin only)",
                "expected": {"patient": 403, "physician": 403, "admin": 200}
            },
            {
                "endpoint": "/auth/roles",
                "method": "GET",
                "description": "Role comparison (public)",
                "expected": {"patient": 200, "physician": 200, "admin": 200}
            }
        ]
        
        async with httpx.AsyncClient() as client:
            for test_case in test_cases:
                print(f"\n  Testing: {test_case['description']}")
                print(f"  Endpoint: {test_case['method']} {test_case['endpoint']}")
                
                for role, token_data in self.tokens.items():
                    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                    
                    try:
                        if test_case['method'] == 'GET':
                            response = await client.get(f"{self.base_url}{test_case['endpoint']}", headers=headers)
                        else:
                            response = await client.post(f"{self.base_url}{test_case['endpoint']}", headers=headers)
                        
                        expected_status = test_case['expected'][role]
                        status_icon = "✅" if response.status_code == expected_status else "❌"
                        
                        print(f"    {status_icon} {role.capitalize()}: {response.status_code} (expected {expected_status})")
                        
                        if response.status_code != expected_status:
                            print(f"       Response: {response.text[:100]}...")
                            
                    except Exception as e:
                        print(f"    ❌ {role.capitalize()}: Error - {e}")
    
    async def test_rate_limiting(self):
        """Test rate limiting for different roles."""
        print(f"\n⏱️  Testing Rate Limiting")
        print("-" * 40)
        
        async with httpx.AsyncClient() as client:
            for role, token_data in self.tokens.items():
                print(f"\n  Testing {role.capitalize()} rate limits:")
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                
                # Get initial rate limit status
                try:
                    response = await client.get(f"{self.base_url}/auth/rate-limit", headers=headers)
                    if response.status_code == 200:
                        limit_info = response.json()
                        print(f"    Initial: {limit_info['requests']['current']}/{limit_info['requests']['limit']} requests")
                        
                        # Make several requests to test limiting
                        max_requests = min(5, limit_info['requests']['limit'] + 2)
                        
                        for i in range(max_requests):
                            test_response = await client.get(f"{self.base_url}/auth/me", headers=headers)
                            if test_response.status_code == 200:
                                print(f"    Request {i+1}: ✅ Allowed")
                            elif test_response.status_code == 429:
                                print(f"    Request {i+1}: ⛔ Rate limited")
                                break
                            else:
                                print(f"    Request {i+1}: ❌ Error ({test_response.status_code})")
                    else:
                        print(f"    ❌ Failed to get rate limit info: {response.status_code}")
                        
                except Exception as e:
                    print(f"    ❌ Error testing rate limits: {e}")
    
    async def test_session_management(self):
        """Test session management features."""
        print(f"\n📋 Testing Session Management")
        print("-" * 40)
        
        async with httpx.AsyncClient() as client:
            for role, token_data in self.tokens.items():
                print(f"\n  {role.capitalize()} session:")
                headers = {
                    "Authorization": f"Bearer {token_data['access_token']}",
                    "X-Session-ID": token_data.get('session_id', '')
                }
                
                try:
                    # Get session info
                    response = await client.get(f"{self.base_url}/auth/session", headers=headers)
                    if response.status_code == 200:
                        session_info = response.json()
                        print(f"    ✅ Session ID: {session_info['session_id'][:16]}...")
                        print(f"    Created: {session_info['created_at']}")
                        print(f"    Requests: {session_info['request_count']}")
                        print(f"    Cost: ${session_info['total_cost_usd']:.4f}")
                    else:
                        print(f"    ❌ Failed to get session info: {response.status_code}")
                        
                except Exception as e:
                    print(f"    ❌ Error getting session info: {e}")
    
    async def demonstrate_different_access_levels(self):
        """Demonstrate how different roles see different information."""
        print(f"\n🎭 Demonstrating Different Access Levels")
        print("-" * 40)
        
        async with httpx.AsyncClient() as client:
            # Get role capabilities
            for role, token_data in self.tokens.items():
                print(f"\n  {role.capitalize()} capabilities:")
                headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                
                try:
                    response = await client.get(f"{self.base_url}/auth/me", headers=headers)
                    if response.status_code == 200:
                        user_info = response.json()
                        capabilities = user_info['capabilities']
                        
                        print(f"    Max queries/hour: {capabilities['max_queries_per_hour']}")
                        print(f"    Allowed models: {', '.join(capabilities['allowed_models'])}")
                        print(f"    Features ({len(capabilities['features'])}):")
                        
                        for feature in capabilities['features'][:5]:  # Show first 5 features
                            print(f"      • {feature}")
                        
                        if len(capabilities['features']) > 5:
                            print(f"      ... and {len(capabilities['features']) - 5} more")
                            
                    else:
                        print(f"    ❌ Failed to get capabilities: {response.status_code}")
                        
                except Exception as e:
                    print(f"    ❌ Error getting capabilities: {e}")
    
    async def run_full_demo(self):
        """Run the complete API RBAC demonstration."""
        print("🌐 Secure Medical Chat - API RBAC Demonstration")
        print("=" * 60)
        
        # Create tokens
        await self.create_demo_tokens()
        
        if not self.tokens:
            print("❌ No tokens created. Make sure the FastAPI server is running on http://localhost:8000")
            return
        
        # Run all tests
        await self.test_authentication()
        await self.test_role_access()
        await self.test_rate_limiting()
        await self.test_session_management()
        await self.demonstrate_different_access_levels()
        
        print(f"\n✅ API RBAC Demo Complete!")
        print("\nTo start the FastAPI server, run:")
        print("  cd phase4-secure-medical-chat")
        print("  python -m uvicorn src.main:app --reload")


async def main():
    """Run the API RBAC demonstration."""
    demo = APIRBACDemo()
    await demo.run_full_demo()


if __name__ == "__main__":
    asyncio.run(main())