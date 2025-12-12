"""
Helicone Cost Tracking Demo

This script demonstrates the Helicone integration for cost tracking and optimization.
It shows:
- Making LLM requests through Helicone proxy
- Automatic cost tracking and storage
- Model routing based on user role
- Cost analytics and reporting
- Cache effectiveness
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from llm.llm_gateway import LLMGateway
from llm.helicone_client import HeliconeConfig
from models import ChatRequest, UserRole


async def demo_helicone_integration():
    """Demonstrate Helicone cost tracking integration."""
    print("🚀 Helicone Cost Tracking Demo")
    print("=" * 50)
    
    # Check for required environment variables
    required_vars = ["OPENAI_API_KEY", "HELICONE_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease set the following environment variables:")
        print("- OPENAI_API_KEY: Your OpenAI API key")
        print("- HELICONE_API_KEY: Your Helicone API key")
        return
    
    # Initialize LLM Gateway with Helicone
    print("🔧 Initializing LLM Gateway with Helicone integration...")
    
    helicone_config = HeliconeConfig(
        api_key=os.getenv("HELICONE_API_KEY"),
        enable_caching=True,
        cache_ttl_seconds=3600,  # 1 hour for demo
        enable_cost_tracking=True
    )
    
    gateway = LLMGateway(
        helicone_config=helicone_config,
        db_path="demo_cost_tracking.db"
    )
    
    print("✅ Gateway initialized successfully")
    
    # Demo requests with different user roles
    demo_requests = [
        {
            "role": UserRole.PATIENT,
            "message": "I have a headache. What could be causing it?",
            "session_id": "patient_session_1"
        },
        {
            "role": UserRole.PHYSICIAN,
            "message": "What are the differential diagnoses for acute chest pain in a 45-year-old male with hypertension?",
            "session_id": "physician_session_1"
        },
        {
            "role": UserRole.ADMIN,
            "message": "Generate a summary of common medication interactions for elderly patients.",
            "session_id": "admin_session_1"
        },
        {
            "role": UserRole.PATIENT,
            "message": "I have a headache. What could be causing it?",  # Duplicate for cache demo
            "session_id": "patient_session_2"
        }
    ]
    
    print("\n📝 Processing demo requests...")
    print("-" * 30)
    
    total_cost = 0.0
    
    for i, req_data in enumerate(demo_requests, 1):
        print(f"\n{i}. Processing {req_data['role'].value} request...")
        
        request = ChatRequest(
            message=req_data["message"],
            user_role=req_data["role"],
            session_id=req_data["session_id"],
            user_id=f"demo_user_{req_data['role'].value}"
        )
        
        try:
            start_time = datetime.now()
            response, metadata = await gateway.process_chat_request(request)
            end_time = datetime.now()
            
            # Display results
            print(f"   ✅ Response received")
            print(f"   💰 Cost: ${metadata['cost']:.4f}")
            print(f"   🕒 Latency: {metadata['latency_ms']}ms")
            print(f"   🤖 Model: {metadata['model_used']}")
            print(f"   💾 Cache Hit: {'Yes' if metadata['cache_hit'] else 'No'}")
            print(f"   🎯 Tokens: {metadata.get('tokens_used', 0)}")
            
            if len(response.response) > 100:
                print(f"   📄 Response: {response.response[:100]}...")
            else:
                print(f"   📄 Response: {response.response}")
            
            total_cost += metadata['cost']
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print(f"\n💰 Total Demo Cost: ${total_cost:.4f}")
    
    # Display cost analytics
    print("\n📊 Cost Analytics")
    print("-" * 20)
    
    try:
        # Get metrics
        metrics = gateway.get_metrics(period_hours=1)  # Last hour
        
        print(f"Total Requests: {metrics['queries_today']}")
        print(f"Cache Hit Rate: {metrics['cache_hit_rate']:.1%}")
        print(f"Average Latency: {metrics['avg_latency_ms']:.0f}ms")
        
        if metrics['cost_by_model']:
            print("\nCost by Model:")
            for model, cost in metrics['cost_by_model'].items():
                print(f"  {model}: ${cost:.4f}")
        
        if metrics['cost_by_role']:
            print("\nCost by Role:")
            for role, cost in metrics['cost_by_role'].items():
                print(f"  {role}: ${cost:.4f}")
        
    except Exception as e:
        print(f"Error getting metrics: {str(e)}")
    
    # Display optimization report
    print("\n🎯 Optimization Report")
    print("-" * 25)
    
    try:
        optimization_report = gateway.get_optimization_report()
        
        print(f"Current Metrics:")
        current = optimization_report['current_metrics']
        print(f"  Total Cost: ${current['total_cost']:.4f}")
        print(f"  Total Requests: {current['total_requests']}")
        print(f"  Avg Cost/Request: ${current['avg_cost_per_request']:.4f}")
        print(f"  Cache Hit Rate: {current['cache_hit_rate']:.1%}")
        
        if optimization_report['recommendations']:
            print(f"\nRecommendations:")
            for rec in optimization_report['recommendations']:
                print(f"  • {rec['title']}")
                print(f"    {rec['description']}")
                if 'potential_savings' in rec:
                    print(f"    Potential Savings: ${rec['potential_savings']:.4f}")
        else:
            print("\n✅ No optimization recommendations at this time")
        
        total_savings = optimization_report.get('total_potential_savings', 0)
        if total_savings > 0:
            print(f"\n💡 Total Potential Savings: ${total_savings:.4f}")
        
    except Exception as e:
        print(f"Error getting optimization report: {str(e)}")
    
    # Display cache statistics
    print("\n💾 Cache Statistics")
    print("-" * 20)
    
    try:
        cache_stats = gateway.get_cache_stats()
        
        print(f"Cache Entries: {cache_stats['total_entries']}")
        print(f"Cache TTL: {cache_stats['cache_ttl_hours']:.1f} hours")
        print(f"Memory Usage: ~{cache_stats['memory_usage_estimate']} bytes")
        
        if cache_stats['age_distribution']:
            print("\nAge Distribution:")
            for age_range, count in cache_stats['age_distribution'].items():
                print(f"  {age_range}: {count} entries")
        
    except Exception as e:
        print(f"Error getting cache stats: {str(e)}")
    
    # Display expensive queries
    print("\n💸 Most Expensive Queries")
    print("-" * 30)
    
    try:
        expensive_queries = gateway.get_expensive_queries(limit=5)
        
        if expensive_queries:
            for i, query in enumerate(expensive_queries, 1):
                print(f"{i}. ${query['cost_usd']:.4f} - {query['model']} - {query['user_role']}")
                print(f"   Tokens: {query['total_tokens']} | Cache Hit: {query['cache_hit']}")
        else:
            print("No expensive queries found")
        
    except Exception as e:
        print(f"Error getting expensive queries: {str(e)}")
    
    # Health check
    print("\n🏥 System Health Check")
    print("-" * 25)
    
    try:
        health = await gateway.health_check()
        
        print(f"Overall Status: {health['overall']}")
        print(f"Gateway: {health['gateway']}")
        print(f"Cost Tracker: {health['cost_tracker']}")
        print(f"Cache: {health['cache']}")
        
        if 'cache_entries' in health:
            print(f"Cache Entries: {health['cache_entries']}")
        
    except Exception as e:
        print(f"Error performing health check: {str(e)}")
    
    print("\n🎉 Demo completed successfully!")
    print("\nKey Features Demonstrated:")
    print("✅ Helicone proxy integration for cost tracking")
    print("✅ Automatic model routing based on user role")
    print("✅ Response caching with configurable TTL")
    print("✅ Persistent cost data storage")
    print("✅ Real-time cost analytics and reporting")
    print("✅ Cost optimization recommendations")
    print("✅ Expensive query identification")
    print("✅ System health monitoring")


def demo_cost_analysis():
    """Demonstrate cost analysis without making API calls."""
    print("\n📈 Cost Analysis Demo (No API Calls)")
    print("=" * 40)
    
    # Initialize gateway for analysis only
    gateway = LLMGateway(db_path="demo_cost_tracking.db")
    
    try:
        # Get detailed analytics
        analytics = gateway.get_detailed_analytics(period_days=1)
        
        print("Analytics Summary:")
        summary = analytics['summary']
        print(f"  Total Cost: ${summary['total_cost_usd']:.4f}")
        print(f"  Total Requests: {summary['total_requests']}")
        print(f"  Cache Hit Rate: {summary['cache_hit_rate']:.1%}")
        
        if analytics['trends']:
            trends = analytics['trends']
            print(f"\nTrends:")
            print(f"  Cost Trend: {trends['cost_trend']}")
            print(f"  Usage Trend: {trends['usage_trend']}")
            print(f"  Efficiency Trend: {trends['efficiency_trend']}")
        
        if analytics['role_analytics']:
            print(f"\nRole Analytics:")
            for role, data in analytics['role_analytics'].items():
                print(f"  {role}: ${data['total_cost']:.4f} ({data['total_requests']} requests)")
        
    except Exception as e:
        print(f"No previous data available: {str(e)}")


if __name__ == "__main__":
    print("Helicone Cost Tracking Integration Demo")
    print("Choose an option:")
    print("1. Full demo with API calls (requires API keys)")
    print("2. Cost analysis only (no API calls)")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(demo_helicone_integration())
    elif choice == "2":
        demo_cost_analysis()
    else:
        print("Invalid choice. Please run again and select 1 or 2.")