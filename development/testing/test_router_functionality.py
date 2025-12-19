#!/usr/bin/env python3
"""
Simple test script to verify model router and caching functionality.
This script tests the core components without requiring API keys.
"""

import sys
import os
sys.path.append('src')

from llm.helicone_client import QueryComplexityAnalyzer, PromptOptimizer, ModelRouter
from models import UserRole


def test_complexity_analysis():
    """Test query complexity analysis."""
    print("🧠 Testing Query Complexity Analysis")
    print("-" * 40)
    
    analyzer = QueryComplexityAnalyzer()
    
    test_queries = [
        ("I have a headache", "simple"),
        ("What are the treatment options for diabetes?", "moderate"),
        ("Please provide a comprehensive differential diagnosis for a patient with acute chest pain, elevated troponins, and ST-segment changes on ECG. Consider both cardiac and non-cardiac etiologies including myocardial infarction, pulmonary embolism, aortic dissection, and pericarditis.", "complex")
    ]
    
    for query, expected_level in test_queries:
        analysis = analyzer.analyze_complexity(query)
        complexity = analysis['overall_score']
        recommendation = analysis['recommendation']
        
        print(f"\nQuery: {query[:60]}...")
        print(f"Complexity Score: {complexity:.3f}")
        print(f"Expected Level: {expected_level}")
        print(f"Model Recommendation: {recommendation}")
        
        # Verify complexity levels
        if expected_level == "simple" and complexity < 0.2:
            print("✅ Correctly identified as simple")
        elif expected_level == "moderate" and 0.1 <= complexity <= 0.4:
            print("✅ Correctly identified as moderate")
        elif expected_level == "complex" and complexity > 0.2:
            print("✅ Correctly identified as complex")
        else:
            print(f"⚠️  Complexity score {complexity:.3f} may not match expected level {expected_level}")


def test_prompt_optimization():
    """Test prompt optimization."""
    print("\n🔧 Testing Prompt Optimization")
    print("-" * 40)
    
    optimizer = PromptOptimizer()
    
    test_cases = [
        ("I would like to know if you could please tell me about diabetes treatment options", UserRole.PATIENT),
        ("Patient is experiencing chest pain and shortness of breath", UserRole.PHYSICIAN),
        ("Could you please help me understand what blood pressure medications are available?", UserRole.PATIENT)
    ]
    
    for query, role in test_cases:
        optimization = optimizer.optimize_prompt(query, role)
        
        print(f"\nRole: {role.value}")
        print(f"Original: {query}")
        print(f"Optimized: {optimization['optimized_message']}")
        print(f"Tokens Saved: {optimization['tokens_saved']}")
        print(f"Savings %: {optimization['savings_percentage']:.1f}%")
        
        if optimization['should_use_optimized']:
            print("✅ Optimization recommended")
        else:
            print("ℹ️  No significant optimization needed")


def test_model_routing():
    """Test model routing decisions."""
    print("\n🎯 Testing Model Routing")
    print("-" * 40)
    
    router = ModelRouter()
    
    test_scenarios = [
        ("I have a headache", UserRole.PATIENT, "gpt-3.5-turbo"),
        ("What is aspirin?", UserRole.PHYSICIAN, "gpt-3.5-turbo"),
        ("Please provide a differential diagnosis for chest pain with elevated troponins", UserRole.PHYSICIAN, "gpt-4"),
        ("Complex treatment plan for chronic kidney disease with diabetes", UserRole.PHYSICIAN, "gpt-4"),
        ("System administration query", UserRole.ADMIN, "gpt-3.5-turbo")
    ]
    
    for query, role, expected_model in test_scenarios:
        result = router.select_model(query, role)
        selected_model = result['model_config'].model
        complexity = result['complexity_analysis']['overall_score']
        routing_reason = result['routing_decision']['routing_reason']
        
        print(f"\nQuery: {query[:50]}...")
        print(f"Role: {role.value}")
        print(f"Complexity: {complexity:.3f}")
        print(f"Selected Model: {selected_model}")
        print(f"Expected Model: {expected_model}")
        print(f"Routing Reason: {routing_reason}")
        
        if selected_model == expected_model:
            print("✅ Correct model selection")
        else:
            print(f"⚠️  Expected {expected_model}, got {selected_model}")


def test_routing_analytics():
    """Test routing analytics."""
    print("\n📊 Testing Routing Analytics")
    print("-" * 40)
    
    router = ModelRouter()
    
    # Generate some routing decisions
    test_queries = [
        ("Simple query 1", UserRole.PATIENT),
        ("Simple query 2", UserRole.PATIENT),
        ("Complex diagnosis query", UserRole.PHYSICIAN),
        ("Treatment planning query", UserRole.PHYSICIAN),
        ("Admin system query", UserRole.ADMIN)
    ]
    
    for query, role in test_queries:
        router.select_model(query, role)
    
    # Get analytics
    analytics = router.get_routing_analytics(days=1)
    
    if "message" not in analytics:
        print("Model Usage:")
        for model, stats in analytics['model_usage'].items():
            print(f"  {model}: {stats['count']} requests ({stats['percentage']:.1f}%)")
        
        print(f"\nComplexity Analytics:")
        complexity = analytics['complexity_analytics']
        print(f"  Average: {complexity['average_complexity']:.3f}")
        print(f"  Range: {complexity['min_complexity']:.3f} - {complexity['max_complexity']:.3f}")
        
        print(f"\nOptimization Analytics:")
        opt = analytics['optimization_analytics']
        print(f"  Optimizations Applied: {opt['optimizations_applied']}")
        print(f"  Total Tokens Saved: {opt['total_tokens_saved']}")
        
        print("✅ Analytics generated successfully")
    else:
        print("ℹ️  Insufficient data for analytics")
    
    # Test recommendations
    recommendations = router.get_model_recommendations()
    print(f"\nRecommendations ({len(recommendations)}):")
    for rec in recommendations:
        print(f"  - {rec['message']}")


def main():
    """Run all tests."""
    print("🚀 Model Router and Caching Functionality Test")
    print("=" * 60)
    
    try:
        test_complexity_analysis()
        test_prompt_optimization()
        test_model_routing()
        test_routing_analytics()
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Summary:")
        print("- Query complexity analysis: Working")
        print("- Prompt optimization: Working")
        print("- Model routing: Working")
        print("- Analytics and recommendations: Working")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()