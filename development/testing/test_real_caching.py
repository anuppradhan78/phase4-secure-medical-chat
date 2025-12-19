#!/usr/bin/env python3
"""
Test real caching effectiveness with actual API calls.
"""

import sys
import os
import asyncio
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append('src')

from llm.llm_gateway import LLMGateway
from llm.helicone_client import HeliconeConfig
from models import ChatRequest, UserRole


async def test_real_caching():
    """Test caching with real API calls."""
    print("🧪 Testing Real Caching with API Calls")
    print("=" * 50)
    
    # Configure gateway
    helicone_config = HeliconeConfig(
        api_key=os.getenv("HELICONE_API_KEY"),
        enable_caching=True,
        cache_ttl_seconds=3600,  # 1 hour
        enable_cost_tracking=True
    )
    
    gateway = LLMGateway(helicone_config=helicone_config)
    
    # Clear cache to start fresh
    gateway.clear_cache()
    print("Cache cleared for testing")
    
    # Test query
    test_query = "What is diabetes? Please provide a brief explanation."
    
    print(f"\nTest Query: {test_query}")
    print("\n" + "="*50)
    
    # First request - should be cache miss
    print("\n1️⃣ First Request (Cache Miss Expected)")
    print("-" * 30)
    
    request1 = ChatRequest(
        message=test_query,
        user_role=UserRole.PATIENT,
        session_id="cache_test_1"
    )
    
    start_time = time.time()
    response1, metadata1 = await gateway.process_chat_request(request1)
    end_time = time.time()
    
    latency1 = (end_time - start_time) * 1000
    
    print(f"Response: {response1.response[:100]}...")
    print(f"Cost: ${metadata1['cost']:.4f}")
    print(f"Latency: {latency1:.0f}ms")
    print(f"Cache Hit: {metadata1['cache_hit']}")
    print(f"Tokens Used: {metadata1['tokens_used']}")
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Second request - should be cache hit
    print("\n2️⃣ Second Request (Cache Hit Expected)")
    print("-" * 30)
    
    request2 = ChatRequest(
        message=test_query,  # Same query
        user_role=UserRole.PATIENT,  # Same role
        session_id="cache_test_2"
    )
    
    start_time = time.time()
    response2, metadata2 = await gateway.process_chat_request(request2)
    end_time = time.time()
    
    latency2 = (end_time - start_time) * 1000
    
    print(f"Response: {response2.response[:100]}...")
    print(f"Cost: ${metadata2['cost']:.4f}")
    print(f"Latency: {latency2:.0f}ms")
    print(f"Cache Hit: {metadata2['cache_hit']}")
    print(f"Tokens Used: {metadata2['tokens_used']}")
    
    # Calculate improvements
    print("\n📊 Caching Performance Analysis")
    print("-" * 30)
    
    latency_improvement = ((latency1 - latency2) / latency1) * 100
    cost_savings = metadata1['cost'] - metadata2['cost']
    
    print(f"Latency Improvement: {latency_improvement:.1f}% ({latency1:.0f}ms → {latency2:.0f}ms)")
    print(f"Cost Savings: ${cost_savings:.4f} ({metadata1['cost']:.4f} → {metadata2['cost']:.4f})")
    print(f"Token Savings: {metadata1['tokens_used'] - metadata2['tokens_used']}")
    
    # Verify cache hit
    if metadata2['cache_hit']:
        print("✅ Cache hit successful!")
    else:
        print("⚠️  Expected cache hit but got cache miss")
    
    # Get cache statistics
    cache_stats = gateway.get_cache_stats()
    print(f"\nCache Statistics:")
    print(f"Hit Rate: {cache_stats['performance_stats']['hit_rate']:.1%}")
    print(f"Total Entries: {cache_stats['basic_stats']['total_entries']}")
    print(f"Cache Hits: {cache_stats['performance_stats']['cache_hits']}")
    print(f"Cache Misses: {cache_stats['performance_stats']['cache_misses']}")
    
    # Test different query (should be cache miss)
    print("\n3️⃣ Different Query (Cache Miss Expected)")
    print("-" * 30)
    
    different_query = "What are the symptoms of hypertension?"
    request3 = ChatRequest(
        message=different_query,
        user_role=UserRole.PATIENT,
        session_id="cache_test_3"
    )
    
    start_time = time.time()
    response3, metadata3 = await gateway.process_chat_request(request3)
    end_time = time.time()
    
    latency3 = (end_time - start_time) * 1000
    
    print(f"Query: {different_query}")
    print(f"Response: {response3.response[:100]}...")
    print(f"Latency: {latency3:.0f}ms")
    print(f"Cache Hit: {metadata3['cache_hit']}")
    
    if not metadata3['cache_hit']:
        print("✅ Correctly identified as cache miss for different query")
    else:
        print("⚠️  Unexpected cache hit for different query")
    
    # Final cache statistics
    final_cache_stats = gateway.get_cache_stats()
    print(f"\nFinal Cache Statistics:")
    print(f"Hit Rate: {final_cache_stats['performance_stats']['hit_rate']:.1%}")
    print(f"Total Requests: {final_cache_stats['performance_stats']['total_requests']}")
    print(f"Cache Entries: {final_cache_stats['basic_stats']['total_entries']}")
    
    return True


async def main():
    """Run the caching test."""
    try:
        await test_real_caching()
        print("\n🎉 Caching test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())