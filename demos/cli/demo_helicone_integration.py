#!/usr/bin/env python3
"""
Helicone Integration Demo for Secure Medical Chat

This script demonstrates the complete Helicone cost tracking integration:
1. LLM Gateway with Helicone proxy
2. Automatic cost tracking and storage
3. Model routing based on user role and complexity
4. Response caching for optimization
5. Cost analytics and reporting
6. Budget monitoring and alerts

Usage:
    python demo_helicone_integration.py

Environment Variables Required:
    OPENAI_API_KEY: Your OpenAI API key
    HELICONE_API_KEY: Your Helicone API key (optional for demo)
"""

import asyncio
import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from llm.llm_gateway import LLMGateway
from llm.helicone_client import HeliconeConfig
from models import ChatRequest, UserRole


async def main():
    """Main demo function."""
    print("🚀 Secure Medical Chat - Helicone Integration Demo")
    print("=" * 60)
    
    # Check environment setup
    print("🔧 Checking Environment Setup...")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    helicone_key = os.getenv("HELICONE_API_KEY")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not found")
        print("   Please set your OpenAI API key:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        return
    
    if not helicone_key:
        print("⚠️  HELICONE_API_KEY not found - using mock cost tracking")
        print("   For full Helicone integration, set:")
        print("   export HELICONE_API_KEY='your-helicone-key-here'")
        helicone_config = None
    else:
        print("✅ Helicone API key found")
        helicone_config = HeliconeConfig(
            api_key=helicone_key,
            enable_caching=True,
            cache_ttl_seconds=3600,  # 1 hour for demo
            enable_cost_tracking=True
        )
    
    print(f"✅ OpenAI API key configured")
    
    # Initialize LLM Gateway
    print("\n🏗️  Initializing LLM Gateway with Cost Tracking...")
    
    try:
        gateway = LLMGateway(
            helicone_config=helicone_config,
            db_path="demo_helicone_costs.db"
        )
        print("✅ LLM Gateway initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize LLM Gateway: {str(e)}")
        return
    
    # Demo scenarios
    demo_scenarios = [
        {
            "name": "Patient Simple Query",
            "role": UserRole.PATIENT,
            "message": "I have a headache. What could be causing it?",
            "expected_model": "gpt-3.5-turbo"
        },
        {
            "name": "Physician Complex Query",
            "role": UserRole.PHYSICIAN,
            "message": "What are the differential diagnoses for acute chest pain in a 45-year-old male with hypertension, diabetes, and a family history of coronary artery disease? Please include both cardiac and non-cardiac causes.",
            "expected_model": "gpt-4"
        },
        {
            "name": "Admin Analytics Query",
            "role": UserRole.ADMIN,
            "message": "Generate a summary of common medication interactions for elderly patients with multiple comorbidities.",
            "expected_model": "gpt-4"
        },
        {
            "name": "Patient Cache Test (Duplicate)",
            "role": UserRole.PATIENT,
            "message": "I have a headache. What could be causing it?",  # Same as first query
            "expected_model": "gpt-3.5-turbo",
            "should_cache": True
        }
    ]
    
    print(f"\n📝 Running {len(demo_scenarios)} Demo Scenarios...")
    print("-" * 50)
    
    total_cost = 0.0
    scenario_results = []
    
    for i, scenario in enumerate(demo_scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   Role: {scenario['role'].value}")
        print(f"   Expected Model: {scenario['expected_model']}")
        
        # Create chat request
        request = ChatRequest(
            message=scenario["message"],
            user_role=scenario["role"],
            session_id=f"demo_session_{scenario['role'].value}",
            user_id=f"demo_user_{i}"
        )
        
        try:
            start_time = datetime.now()
            
            # Process request through gateway
            response, metadata = await gateway.process_chat_request(request)
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Display results
            print(f"   ✅ Response received in {processing_time:.2f}s")
            print(f"   💰 Cost: ${metadata['cost']:.4f}")
            print(f"   🤖 Model Used: {metadata['model_used']}")
            print(f"   💾 Cache Hit: {'Yes' if metadata['cache_hit'] else 'No'}")
            print(f"   🎯 Tokens: {metadata.get('tokens_used', 0)}")
            print(f"   🕒 Latency: {metadata['latency_ms']}ms")
            
            # Verify model selection
            if metadata['model_used'] == scenario['expected_model']:
                print(f"   ✅ Model selection correct")
            else:
                print(f"   ⚠️  Expected {scenario['expected_model']}, got {metadata['model_used']}")
            
            # Verify caching
            if scenario.get('should_cache') and metadata['cache_hit']:
                print(f"   ✅ Cache working correctly")
            elif scenario.get('should_cache') and not metadata['cache_hit']:
                print(f"   ⚠️  Expected cache hit, but got cache miss")
            
            # Show response preview
            response_preview = response.response[:100] + "..." if len(response.response) > 100 else response.response
            print(f"   📄 Response: {response_preview}")
            
            total_cost += metadata['cost']
            
            scenario_results.append({
                "scenario": scenario['name'],
                "cost": metadata['cost'],
                "model": metadata['model_used'],
                "cache_hit": metadata['cache_hit'],
                "tokens": metadata.get('tokens_used', 0),
                "latency_ms": metadata['latency_ms']
            })
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            scenario_results.append({
                "scenario": scenario['name'],
                "error": str(e)
            })
    
    print(f"\n💰 Total Demo Cost: ${total_cost:.4f}")
    
    # Display comprehensive analytics
    print("\n📊 Cost Analytics & Reporting")
    print("=" * 40)
    
    try:
        # Get real-time metrics
        print("\n📈 Real-time Metrics:")
        metrics = gateway.get_metrics(period_hours=1)
        
        print(f"   Total Requests: {metrics['queries_today']}")
        print(f"   Total Cost: ${metrics['total_cost_usd']:.4f}")
        print(f"   Cache Hit Rate: {metrics['cache_hit_rate']:.1%}")
        print(f"   Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
        
        if metrics.get('cost_by_model'):
            print(f"\n   Cost by Model:")
            for model, cost in metrics['cost_by_model'].items():
                print(f"     {model}: ${cost:.4f}")
        
        if metrics.get('cost_by_role'):
            print(f"\n   Cost by Role:")
            for role, cost in metrics['cost_by_role'].items():
                print(f"     {role}: ${cost:.4f}")
        
    except Exception as e:
        print(f"   ❌ Error getting metrics: {str(e)}")
    
    # Optimization report
    print("\n🎯 Cost Optimization Report:")
    
    try:
        optimization = gateway.get_optimization_report()
        
        current = optimization['current_metrics']
        print(f"   Current Efficiency:")
        print(f"     Avg Cost/Request: ${current['avg_cost_per_request']:.4f}")
        print(f"     Cache Hit Rate: {current['cache_hit_rate']:.1%}")
        
        if optimization['recommendations']:
            print(f"\n   Recommendations:")
            for rec in optimization['recommendations'][:3]:  # Show top 3
                print(f"     • {rec['title']}")
                print(f"       {rec['description']}")
                if 'potential_savings' in rec:
                    print(f"       Potential Savings: ${rec['potential_savings']:.4f}")
        else:
            print(f"   ✅ No optimization recommendations")
        
        total_savings = optimization.get('total_potential_savings', 0)
        if total_savings > 0:
            print(f"\n   💡 Total Potential Savings: ${total_savings:.4f}")
        
    except Exception as e:
        print(f"   ❌ Error getting optimization report: {str(e)}")
    
    # Expensive queries analysis
    print("\n💸 Expensive Queries Analysis:")
    
    try:
        expensive = gateway.get_expensive_queries(limit=5)
        
        if expensive:
            for i, query in enumerate(expensive, 1):
                print(f"   {i}. ${query['cost_usd']:.4f} - {query['model']} - {query['user_role']}")
                print(f"      Tokens: {query['total_tokens']} | Cache: {'Hit' if query['cache_hit'] else 'Miss'}")
        else:
            print(f"   No expensive queries found")
        
    except Exception as e:
        print(f"   ❌ Error getting expensive queries: {str(e)}")
    
    # Budget monitoring demo
    print("\n💳 Budget Monitoring Demo:")
    
    try:
        # Test budget alert with low threshold
        budget_status = gateway.check_budget_alert(
            budget_limit=0.01,  # Very low threshold for demo
            period_hours=1
        )
        
        print(f"   Budget Limit: ${budget_status['budget_limit']:.4f}")
        print(f"   Current Cost: ${budget_status['current_cost']:.4f}")
        print(f"   Utilization: {budget_status['utilization_percent']:.1f}%")
        print(f"   Budget Exceeded: {'Yes' if budget_status['budget_exceeded'] else 'No'}")
        
        if budget_status['budget_exceeded']:
            print(f"   ⚠️  Budget alert would be triggered!")
        else:
            print(f"   ✅ Within budget limits")
        
    except Exception as e:
        print(f"   ❌ Error checking budget: {str(e)}")
    
    # Cache statistics
    print("\n💾 Cache Performance:")
    
    try:
        cache_stats = gateway.get_cache_stats()
        
        print(f"   Cache Entries: {cache_stats['total_entries']}")
        print(f"   Cache TTL: {cache_stats['cache_ttl_hours']:.1f} hours")
        print(f"   Memory Usage: ~{cache_stats['memory_usage_estimate']} bytes")
        
        if cache_stats['age_distribution']:
            print(f"   Age Distribution:")
            for age_range, count in cache_stats['age_distribution'].items():
                if count > 0:
                    print(f"     {age_range}: {count} entries")
        
    except Exception as e:
        print(f"   ❌ Error getting cache stats: {str(e)}")
    
    # System health check
    print("\n🏥 System Health Check:")
    
    try:
        health = await gateway.health_check()
        
        print(f"   Overall Status: {health['overall']}")
        print(f"   Gateway: {health['gateway']}")
        print(f"   Cost Tracker: {health['cost_tracker']}")
        print(f"   Cache: {health['cache']}")
        
    except Exception as e:
        print(f"   ❌ Error performing health check: {str(e)}")
    
    # Summary
    print(f"\n🎉 Demo Completed Successfully!")
    print("=" * 40)
    
    print(f"\n📋 Summary:")
    print(f"   Scenarios Executed: {len(scenario_results)}")
    print(f"   Total Cost: ${total_cost:.4f}")
    print(f"   Models Used: {set(r.get('model', 'unknown') for r in scenario_results if 'model' in r)}")
    
    successful_scenarios = [r for r in scenario_results if 'error' not in r]
    if successful_scenarios:
        avg_latency = sum(r['latency_ms'] for r in successful_scenarios) / len(successful_scenarios)
        cache_hits = sum(1 for r in successful_scenarios if r['cache_hit'])
        cache_rate = cache_hits / len(successful_scenarios) * 100
        
        print(f"   Average Latency: {avg_latency:.0f}ms")
        print(f"   Cache Hit Rate: {cache_rate:.1f}%")
    
    print(f"\n✅ Key Features Demonstrated:")
    print(f"   • Helicone proxy integration for cost tracking")
    print(f"   • Intelligent model routing (Patient→GPT-3.5, Physician/Admin→GPT-4)")
    print(f"   • Response caching with TTL")
    print(f"   • Persistent cost data storage")
    print(f"   • Real-time analytics and reporting")
    print(f"   • Cost optimization recommendations")
    print(f"   • Budget monitoring and alerts")
    print(f"   • System health monitoring")
    
    print(f"\n💾 Data Stored:")
    print(f"   Cost tracking database: demo_helicone_costs.db")
    print(f"   View data with: sqlite3 demo_helicone_costs.db '.tables'")
    
    # Export results for analysis
    results_file = "demo_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_cost": total_cost,
            "scenarios": scenario_results,
            "summary": {
                "scenarios_executed": len(scenario_results),
                "successful_scenarios": len(successful_scenarios),
                "total_cost": total_cost
            }
        }, f, indent=2)
    
    print(f"   Results exported to: {results_file}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()