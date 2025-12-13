#!/usr/bin/env python3
"""
Simple test to check if modules can be imported.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test importing all modules."""
    print("Testing module imports...")
    
    try:
        print("✅ Importing models...")
        from src.models import ChatRequest, ChatResponse, UserRole
        
        print("✅ Importing RBAC...")
        from src.auth.rbac import RBACService
        
        print("✅ Importing rate limiter...")
        from src.auth.rate_limiter import RateLimiter
        
        print("✅ Importing mock PII service...")
        from src.security.mock_pii_redaction import MockPIIRedactionService
        
        print("✅ Importing guardrails...")
        from src.security.guardrails import GuardrailsService
        
        print("✅ Importing medical safety...")
        from src.security.medical_safety import MedicalSafetyController
        
        print("✅ Importing mock LLM gateway...")
        from src.llm.mock_llm_gateway import MockLLMGateway
        
        print("✅ Importing database...")
        from src.database import get_database
        
        print("✅ Importing chat API...")
        from src.api.chat import router
        
        print("✅ All imports successful!")
        
        # Test basic functionality
        print("\nTesting basic functionality...")
        
        rbac = RBACService()
        print(f"✅ RBAC service created with {len(rbac.ROLE_CONFIGS)} roles")
        
        rate_limiter = RateLimiter()
        print("✅ Rate limiter created")
        
        pii_service = MockPIIRedactionService()
        print("✅ Mock PII service created")
        
        guardrails = GuardrailsService()
        print("✅ Guardrails service created")
        
        medical_safety = MedicalSafetyController()
        print("✅ Medical safety controller created")
        
        llm_gateway = MockLLMGateway()
        print("✅ Mock LLM gateway created")
        
        print("\n🎉 All tests passed! The chat endpoint should work.")
        
    except Exception as e:
        print(f"❌ Import error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_imports()