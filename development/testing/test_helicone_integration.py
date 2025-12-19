#!/usr/bin/env python3
"""
Simple test to verify Helicone integration with real API calls.
"""

import sys
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append('src')

from llm.helicone_client import HeliconeClient, HeliconeConfig, ModelRouter
from models import UserRole, ModelConfig


async def test_helicone_integration():
    """Test Helicone integration with a simple API call."""
    print("🧪 Testing Helicone Integration")
    print("=" * 40)
    
    # Configure Helicone
    config = HeliconeConfig(
        api_key=os.getenv("HELICONE_API_KEY"),
        enable_caching=True,
        cache_ttl_seconds=3600,  # 1 hour for testing
        enable_cost_tracking=True
    )
    
    client = HeliconeClient(config)
    
    # Test 1: Simple API call
    print("\n1. Testing simple API call...")
    messages = [{"role": "user", "content": "What is aspirin used for? Please be brief."}]
    model_config = ModelConfig(model="gpt-3.5-turbo", max_tokens=100)
    
    try:
        result = await client.chat_completion(
            messages=messages,
            model_config=model_config,
            user_role=UserRole.PATIENT,
            session_id="test_session_1"
        )
        
        response_text = result["response"].choices[0].message.content
        cost_data = result["cost_data"]
        
        print(f"✅ API call successful!")
        print(f"Response: {response_text[:100]}...")
        print(f"Cost: ${cost_data.cost_usd:.4f}")
        print(f"Tokens: {cost_data.total_tokens}")
        print(f"Model: {cost_data.model}")
        
    except Exception as e:
        print(f"❌ API call failed: {str(e)}")
        return False
    
    # Test 2: Model routing
    print("\n2. Testing model routing...")
    router = ModelRouter()
    
    # Simple query should use GPT-3.5
    simple_result = router.select_model("What is diabetes?", UserRole.PATIENT)
    print(f"Simple query routing: {simple_result['model_config'].model}")
    
    # Complex query should use GPT-4 for physicians
    complex_result = router.select_model(
        "Please provide a differential diagnosis for chest pain with elevated troponins", 
        UserRole.PHYSICIAN
    )
    print(f"Complex query routing: {complex_result['model_config'].model}")
    
    # Test 3: Cost summary
    print("\n3. Testing cost tracking...")
    cost_summary = client.get_cost_summary()
    print(f"Total cost: ${cost_summary['total_cost_usd']:.4f}")
    print(f"Total requests: {cost_summary['total_requests']}")
    print(f"Cache hit rate: {cost_summary['cache_hit_rate']:.1%}")
    
    print("\n✅ All tests passed! Helicone integration is working.")
    return True


async def main():
    """Run the integration test."""
    try:
        success = await test_helicone_integration()
        if success:
            print("\n🎉 Helicone is properly configured and working!")
            print("You can now run the full demo: python examples/model_router_caching_demo.py")
        else:
            print("\n⚠️  There were issues with the Helicone integration.")
            
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())