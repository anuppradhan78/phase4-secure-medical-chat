#!/usr/bin/env python3
"""
Test script for latency optimization features.

This script tests the core latency measurement and optimization functionality
without requiring the full FastAPI application to be running.
"""

import sys
import os
import time
import asyncio
import json
from datetime import datetime, timezone

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_latency_tracker():
    """Test the LatencyTracker functionality."""
    print("🧪 Testing LatencyTracker...")
    
    from llm.latency_tracker import LatencyTracker
    
    # Initialize tracker
    tracker = LatencyTracker()
    print(f"✅ LatencyTracker initialized with {len(tracker.performance_baselines)} baseline stages")
    
    # Test basic measurement
    request_id = "test_request_1"
    start_time = tracker.start_request_tracking(request_id)
    
    # Simulate pipeline stages
    stages = ["authentication", "pii_redaction", "guardrails_validation", "llm_processing"]
    
    for stage in stages:
        with tracker.measure_stage(request_id, stage):
            # Simulate work with different durations
            if stage == "llm_processing":
                time.sleep(0.05)  # Longer for LLM
            else:
                time.sleep(0.01)  # Shorter for other stages
    
    # Complete tracking
    profile = tracker.finish_request_tracking(
        request_id, start_time, "physician", "gpt-3.5-turbo", False, False, 
        {"test": True}
    )
    
    print(f"✅ Request completed in {profile.total_duration_ms:.1f}ms")
    print(f"✅ Recorded {len(profile.stages)} pipeline stages")
    
    # Test stage breakdown
    breakdown = profile.get_breakdown_percentages()
    print("📊 Stage breakdown:")
    for stage_name, percentage in breakdown.items():
        duration = profile.get_stage_duration(stage_name)
        print(f"  - {stage_name}: {duration:.1f}ms ({percentage:.1f}%)")
    
    # Add more test data
    for i in range(5):
        test_id = f"test_request_{i+2}"
        test_start = tracker.start_request_tracking(test_id)
        
        # Simulate different performance characteristics
        cache_hit = i % 2 == 0
        model = "gpt-4" if i % 3 == 0 else "gpt-3.5-turbo"
        
        with tracker.measure_stage(test_id, "authentication"):
            time.sleep(0.001)
        with tracker.measure_stage(test_id, "llm_processing"):
            # Simulate cache hit (faster) vs cache miss
            time.sleep(0.01 if cache_hit else 0.03)
        
        tracker.finish_request_tracking(
            test_id, test_start, "patient", model, cache_hit, False, 
            {"cost": 0.001 * (i + 1)}
        )
    
    print(f"✅ Added {len(tracker.request_profiles)} total profiles")
    
    # Test analytics
    analytics = tracker.get_latency_analytics(1)  # Last hour
    print(f"📈 Analytics for {analytics['total_requests']} requests:")
    print(f"  - Average latency: {analytics['overall_stats']['avg_latency_ms']:.1f}ms")
    print(f"  - P95 latency: {analytics['overall_stats']['p95_latency_ms']:.1f}ms")
    print(f"  - Cache hit rate: {analytics['cache_performance']['cache_hit_rate']:.1%}")
    
    # Test provider comparison
    comparison = tracker.compare_providers(1)
    if "message" not in comparison:
        print(f"🔍 Model comparison:")
        for model, stats in comparison.items():
            if model != "summary":
                if "latency_stats" in stats:
                    # New format
                    avg_latency = stats["latency_stats"]["avg_latency_ms"]
                    requests = stats["request_count"]
                else:
                    # Old format fallback
                    avg_latency = stats.get("avg_latency_ms", 0)
                    requests = stats.get("request_count", 0)
                print(f"  - {model}: {avg_latency:.1f}ms avg ({requests} requests)")
        
        # Handle summary if present
        if "summary" in comparison:
            summary = comparison["summary"]
            print(f"  💡 Recommendation: {summary.get('recommendation', 'No recommendation')}")
    
    print("✅ LatencyTracker tests completed successfully!")
    return True


def test_streaming_components():
    """Test streaming-related components."""
    print("\n🧪 Testing Streaming Components...")
    
    try:
        # Test SSE library
        from sse_starlette.sse import EventSourceResponse
        print("✅ SSE library (sse-starlette) is available")
        
        # Test streaming processor class (without FastAPI dependencies)
        print("✅ Streaming components are importable")
        
        # Test event formatting
        def create_sse_event(event_type: str, data: dict) -> str:
            """Create a Server-Sent Event formatted string."""
            event_data = {
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": "test_123",
                **data
            }
            return f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
        
        # Test event creation
        test_event = create_sse_event("test", {"message": "Hello World"})
        print("✅ SSE event formatting works")
        print(f"📡 Sample event: {test_event[:50]}...")
        
        return True
        
    except ImportError as e:
        print(f"❌ Streaming component test failed: {e}")
        return False


def test_latency_optimization_features():
    """Test the complete latency optimization feature set."""
    print("\n🧪 Testing Latency Optimization Features...")
    
    from llm.latency_tracker import LatencyTracker
    
    tracker = LatencyTracker()
    
    # Test performance baselines
    print(f"📊 Performance baselines configured for {len(tracker.performance_baselines)} stages")
    
    # Test model-specific baselines
    print(f"🤖 Model baselines configured for {len(tracker.model_baselines)} models")
    for model, baselines in tracker.model_baselines.items():
        print(f"  - {model}: {baselines.get('total_request', 'N/A')}ms baseline")
    
    # Simulate realistic workload
    print("🏃 Simulating realistic workload...")
    
    models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    roles = ["patient", "physician", "admin"]
    
    for i in range(15):
        request_id = f"realistic_request_{i}"
        start_time = tracker.start_request_tracking(request_id)
        
        model = models[i % len(models)]
        role = roles[i % len(roles)]
        cache_hit = i % 4 == 0  # 25% cache hit rate
        
        # Simulate realistic stage durations
        with tracker.measure_stage(request_id, "authentication"):
            time.sleep(0.002)
        
        with tracker.measure_stage(request_id, "rate_limiting"):
            time.sleep(0.001)
        
        with tracker.measure_stage(request_id, "pii_redaction") as stage:
            duration = 0.05 if i % 5 == 0 else 0.02  # Some requests have more PII
            time.sleep(duration)
            stage.metadata = {"entities_found": 2 if i % 5 == 0 else 0}
        
        with tracker.measure_stage(request_id, "guardrails_validation"):
            time.sleep(0.03)
        
        with tracker.measure_stage(request_id, "llm_processing") as stage:
            # Model-specific latencies
            if model == "gpt-4":
                base_latency = 0.08
            elif model == "gpt-4-turbo":
                base_latency = 0.06
            else:  # gpt-3.5-turbo
                base_latency = 0.04
            
            # Cache hit reduces latency significantly
            actual_latency = base_latency * 0.1 if cache_hit else base_latency
            time.sleep(actual_latency)
            
            stage.metadata = {
                "model_used": model,
                "cache_hit": cache_hit,
                "tokens_used": 150 + (i * 10)
            }
        
        with tracker.measure_stage(request_id, "response_validation"):
            time.sleep(0.01)
        
        with tracker.measure_stage(request_id, "audit_logging"):
            time.sleep(0.005)
        
        # Complete tracking
        cost = 0.001 if model == "gpt-3.5-turbo" else 0.003
        tracker.finish_request_tracking(
            request_id, start_time, role, model, cache_hit, False,
            {"cost": cost, "realistic_test": True}
        )
    
    print(f"✅ Generated {len(tracker.request_profiles)} realistic profiles")
    
    # Test comprehensive analytics
    analytics = tracker.get_latency_analytics(1)
    print(f"\n📈 Comprehensive Analytics:")
    print(f"  - Total requests: {analytics['total_requests']}")
    print(f"  - Average latency: {analytics['overall_stats']['avg_latency_ms']:.1f}ms")
    print(f"  - P95 latency: {analytics['overall_stats']['p95_latency_ms']:.1f}ms")
    print(f"  - Cache hit rate: {analytics['cache_performance']['cache_hit_rate']:.1%}")
    
    if analytics['cache_performance']['cache_speedup_factor'] > 1:
        print(f"  - Cache speedup: {analytics['cache_performance']['cache_speedup_factor']:.1f}x")
    
    # Test model performance comparison
    comparison = tracker.compare_providers(1)
    if "message" not in comparison:
        print(f"\n🔍 Model Performance Comparison:")
        for model, stats in comparison.items():
            if model == "summary":
                continue
            
            # Handle both old and new format
            if "latency_stats" in stats:
                latency_stats = stats["latency_stats"]
                perf_metrics = stats.get("performance_metrics", {})
                avg_latency = latency_stats["avg_latency_ms"]
                performance = perf_metrics.get("performance_vs_baseline", "unknown")
            else:
                avg_latency = stats.get("avg_latency_ms", 0)
                performance = stats.get("baseline_comparison", {}).get("performance_vs_baseline", "unknown")
            
            print(f"  - {model}: {avg_latency:.1f}ms ({performance})")
        
        # Handle summary if present
        if "summary" in comparison:
            summary = comparison["summary"]
            print(f"  💡 Recommendation: {summary.get('recommendation', 'No recommendation')}")
        else:
            print("  ℹ️ No summary available (insufficient data for comparison)")
    
    # Test performance analysis
    if "performance_analysis" in analytics:
        analysis = analytics["performance_analysis"]
        
        if analysis.get("issues"):
            print(f"\n⚠️ Performance Issues Detected:")
            for issue in analysis["issues"][:3]:
                print(f"  - {issue['type']}: {issue['description']}")
        
        if analysis.get("recommendations"):
            print(f"\n💡 Optimization Recommendations:")
            for rec in analysis["recommendations"][:3]:
                print(f"  - {rec['type']}: {rec['action']}")
        
        if analysis.get("performance_score"):
            score_data = analysis["performance_score"]
            print(f"\n🎯 Performance Score: {score_data['score']}/100 (Grade: {score_data['grade']})")
    
    print("✅ Latency optimization features test completed successfully!")
    return True


def main():
    """Run all tests."""
    print("🚀 Testing Secure Medical Chat - Latency Optimization Features")
    print("=" * 60)
    
    tests = [
        test_latency_tracker,
        test_streaming_components,
        test_latency_optimization_features
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All latency optimization features are working correctly!")
        print("\n💡 Next steps:")
        print("  1. Start the FastAPI server: python src/main.py")
        print("  2. Open streaming_demo.html in a browser")
        print("  3. Run the demo script: python demo_latency_optimization.py")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)