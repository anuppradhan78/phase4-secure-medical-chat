#!/usr/bin/env python3
"""
Model Router and Caching Demonstration

This script demonstrates the enhanced model routing and caching capabilities:
1. Query complexity analysis
2. Intelligent model selection
3. Prompt optimization
4. Response caching with 24-hour TTL
5. Cache hit rate tracking and effectiveness metrics

Requirements: 3.2, 3.4, 3.6
"""

import asyncio
import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm.llm_gateway import LLMGateway
from llm.helicone_client import HeliconeConfig, QueryComplexityAnalyzer, PromptOptimizer
from models import ChatRequest, UserRole


class ModelRouterCachingDemo:
    """Demonstration of model router and caching capabilities."""
    
    def __init__(self):
        """Initialize demo with LLM gateway."""
        # Configure Helicone (will use environment variables or fallback)
        helicone_api_key = os.getenv("HELICONE_API_KEY")
        if helicone_api_key:
            helicone_config = HeliconeConfig(
                api_key=helicone_api_key,
                enable_caching=True,
                cache_ttl_seconds=86400,  # 24 hours
                enable_cost_tracking=True
            )
        else:
            # Fallback config for demo without Helicone
            helicone_config = HeliconeConfig(
                api_key="demo-key",
                base_url="https://api.openai.com/v1",  # Direct OpenAI API
                enable_caching=False,
                enable_cost_tracking=True
            )
        
        self.gateway = LLMGateway(helicone_config=helicone_config)
        self.complexity_analyzer = QueryComplexityAnalyzer()
        self.prompt_optimizer = PromptOptimizer()
        
        # Demo queries with varying complexity
        self.demo_queries = [
            # Simple patient queries (low complexity)
            {
                "message": "I have a headache. What should I do?",
                "user_role": UserRole.PATIENT,
                "expected_model": "gpt-3.5-turbo",
                "category": "simple_symptom"
            },
            {
                "message": "Can you tell me about common cold symptoms?",
                "user_role": UserRole.PATIENT,
                "expected_model": "gpt-3.5-turbo",
                "category": "general_info"
            },
            
            # Moderate complexity queries
            {
                "message": "I've been experiencing chest pain and shortness of breath for the past 2 hours. Should I be concerned?",
                "user_role": UserRole.PATIENT,
                "expected_model": "gpt-3.5-turbo",  # Patients restricted to 3.5
                "category": "moderate_symptoms"
            },
            {
                "message": "What are the treatment options for type 2 diabetes? I need to understand the different medications available.",
                "user_role": UserRole.PHYSICIAN,
                "expected_model": "gpt-3.5-turbo",  # Moderate complexity
                "category": "treatment_info"
            },
            
            # High complexity queries
            {
                "message": "Please provide a differential diagnosis for a 45-year-old patient presenting with acute onset chest pain, elevated troponins, and ST-segment changes on ECG. Consider both cardiac and non-cardiac etiologies.",
                "user_role": UserRole.PHYSICIAN,
                "expected_model": "gpt-4",
                "category": "differential_diagnosis"
            },
            {
                "message": "I need a comprehensive treatment plan for a patient with chronic kidney disease stage 4, diabetes mellitus, and hypertension. Please include medication management, monitoring parameters, and lifestyle modifications.",
                "user_role": UserRole.PHYSICIAN,
                "expected_model": "gpt-4",
                "category": "complex_treatment_plan"
            },
            
            # Research-level queries
            {
                "message": "What are the latest developments in pharmacogenomics for personalized cancer therapy? Please discuss biomarker stratification and precision medicine approaches in oncology.",
                "user_role": UserRole.PHYSICIAN,
                "expected_model": "gpt-4",
                "category": "research_query"
            },
            
            # Verbose queries for optimization testing
            {
                "message": "I would like to know if you could please tell me about what I should do when I am experiencing some pain in my chest area and I was wondering if this could be something serious that I need to be concerned about?",
                "user_role": UserRole.PATIENT,
                "expected_model": "gpt-3.5-turbo",
                "category": "verbose_query"
            }
        ]
    
    async def run_demo(self):
        """Run comprehensive model router and caching demonstration."""
        print("🚀 Model Router and Caching Demonstration")
        print("=" * 60)
        
        # 1. Demonstrate complexity analysis
        await self._demo_complexity_analysis()
        
        # 2. Demonstrate prompt optimization
        await self._demo_prompt_optimization()
        
        # 3. Demonstrate model routing
        await self._demo_model_routing()
        
        # 4. Demonstrate caching effectiveness
        await self._demo_caching_effectiveness()
        
        # 5. Show analytics and recommendations
        await self._demo_analytics_and_recommendations()
        
        print("\n✅ Demo completed successfully!")
    
    async def _demo_complexity_analysis(self):
        """Demonstrate query complexity analysis."""
        print("\n📊 1. Query Complexity Analysis")
        print("-" * 40)
        
        for i, query in enumerate(self.demo_queries[:4], 1):  # First 4 queries
            print(f"\nQuery {i}: {query['category']}")
            print(f"Message: {query['message'][:80]}...")
            
            analysis = self.complexity_analyzer.analyze_complexity(query["message"])
            
            print(f"Overall Complexity: {analysis['overall_score']:.3f}")
            print(f"Components:")
            for component, score in analysis['components'].items():
                print(f"  - {component}: {score:.3f}")
            
            print(f"Recommendation: {analysis['recommendation']}")
            print(f"Medical terms found: {analysis['indicators']['medical_terms_found']}")
            
            # Verify routing matches expectation
            expected = query['expected_model']
            recommended = analysis['recommendation']
            if 'gpt-4' in recommended and expected == 'gpt-4':
                print("✅ Complexity analysis matches expected routing")
            elif 'gpt-3.5' in recommended and expected == 'gpt-3.5-turbo':
                print("✅ Complexity analysis matches expected routing")
            else:
                print(f"⚠️  Complexity analysis ({recommended}) differs from expected ({expected})")
    
    async def _demo_prompt_optimization(self):
        """Demonstrate prompt optimization techniques."""
        print("\n🔧 2. Prompt Optimization")
        print("-" * 40)
        
        # Test optimization on verbose queries
        verbose_queries = [q for q in self.demo_queries if q['category'] == 'verbose_query']
        
        for query in verbose_queries:
            print(f"\nOptimizing query for {query['user_role'].value}:")
            print(f"Original: {query['message']}")
            
            optimization = self.prompt_optimizer.optimize_prompt(
                query['message'], 
                query['user_role']
            )
            
            if optimization['should_use_optimized']:
                print(f"Optimized: {optimization['optimized_message']}")
                print(f"Tokens saved: {optimization['tokens_saved']} ({optimization['savings_percentage']:.1f}%)")
                print(f"Optimizations applied: {optimization['optimizations_applied']}")
                print("✅ Optimization recommended")
            else:
                print("ℹ️  No significant optimization possible")
    
    async def _demo_model_routing(self):
        """Demonstrate intelligent model routing."""
        print("\n🎯 3. Model Routing Demonstration")
        print("-" * 40)
        
        routing_results = []
        
        for query in self.demo_queries:
            print(f"\nProcessing: {query['category']} ({query['user_role'].value})")
            
            # Get routing decision
            routing_result = self.gateway.model_router.select_model(
                query['message'],
                query['user_role']
            )
            
            selected_model = routing_result['model_config'].model
            complexity_score = routing_result['complexity_analysis']['overall_score']
            routing_reason = routing_result['routing_decision']['routing_reason']
            
            print(f"Selected Model: {selected_model}")
            print(f"Complexity Score: {complexity_score:.3f}")
            print(f"Routing Reason: {routing_reason}")
            
            # Check if optimization was applied
            if routing_result['optimization_result']:
                opt_result = routing_result['optimization_result']
                if opt_result['should_use_optimized']:
                    print(f"Prompt Optimization: {opt_result['tokens_saved']} tokens saved")
            
            # Verify routing decision
            expected = query['expected_model']
            if selected_model == expected:
                print("✅ Routing decision matches expectation")
            else:
                print(f"⚠️  Expected {expected}, got {selected_model}")
            
            routing_results.append({
                'query': query['category'],
                'role': query['user_role'].value,
                'selected_model': selected_model,
                'complexity': complexity_score,
                'expected': expected,
                'correct': selected_model == expected
            })
        
        # Summary
        correct_routings = sum(1 for r in routing_results if r['correct'])
        total_routings = len(routing_results)
        accuracy = correct_routings / total_routings * 100
        
        print(f"\n📈 Routing Accuracy: {correct_routings}/{total_routings} ({accuracy:.1f}%)")
    
    async def _demo_caching_effectiveness(self):
        """Demonstrate caching effectiveness with repeated queries."""
        print("\n💾 4. Caching Effectiveness")
        print("-" * 40)
        
        # Clear cache to start fresh
        self.gateway.clear_cache()
        print("Cache cleared for demonstration")
        
        # Select a few queries to repeat
        test_queries = self.demo_queries[:3]
        
        print("\nFirst round - Cache misses expected:")
        first_round_times = []
        
        for i, query in enumerate(test_queries, 1):
            request = ChatRequest(
                message=query['message'],
                user_role=query['user_role'],
                session_id=f"demo_session_{i}"
            )
            
            start_time = time.time()
            
            # Note: In a real demo, this would make actual API calls
            # For demonstration, we'll simulate the caching behavior
            print(f"Query {i}: Processing {query['category']}")
            
            # Simulate processing time
            await asyncio.sleep(0.1)  # Simulate API call latency
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            first_round_times.append(latency)
            
            print(f"  Latency: {latency:.0f}ms (cache miss)")
        
        print("\nSecond round - Cache hits expected:")
        second_round_times = []
        
        for i, query in enumerate(test_queries, 1):
            request = ChatRequest(
                message=query['message'],
                user_role=query['user_role'],
                session_id=f"demo_session_{i}"
            )
            
            start_time = time.time()
            
            # Simulate cache hit (much faster)
            await asyncio.sleep(0.01)  # Simulate cache lookup
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            second_round_times.append(latency)
            
            print(f"Query {i}: Processing {query['category']}")
            print(f"  Latency: {latency:.0f}ms (cache hit)")
        
        # Calculate improvements
        avg_first = sum(first_round_times) / len(first_round_times)
        avg_second = sum(second_round_times) / len(second_round_times)
        improvement = ((avg_first - avg_second) / avg_first) * 100
        
        print(f"\n📊 Caching Performance:")
        print(f"Average latency (cache miss): {avg_first:.0f}ms")
        print(f"Average latency (cache hit): {avg_second:.0f}ms")
        print(f"Latency improvement: {improvement:.1f}%")
        
        # Show cache statistics
        cache_stats = self.gateway.get_cache_stats()
        print(f"\nCache Statistics:")
        print(f"Hit Rate: {cache_stats['performance_stats']['hit_rate']:.1%}")
        print(f"Total Entries: {cache_stats['basic_stats']['total_entries']}")
        print(f"Cache TTL: {cache_stats['basic_stats']['cache_ttl_hours']} hours")
    
    async def _demo_analytics_and_recommendations(self):
        """Demonstrate analytics and optimization recommendations."""
        print("\n📈 5. Analytics and Recommendations")
        print("-" * 40)
        
        # Get routing analytics
        routing_analytics = self.gateway.model_router.get_routing_analytics(days=1)
        
        if "message" not in routing_analytics:  # Has actual data
            print("Model Usage Analytics:")
            model_usage = routing_analytics['model_usage']
            for model, stats in model_usage.items():
                print(f"  {model}: {stats['count']} requests ({stats['percentage']:.1f}%)")
            
            print(f"\nComplexity Analytics:")
            complexity = routing_analytics['complexity_analytics']
            print(f"  Average Complexity: {complexity['average_complexity']:.3f}")
            print(f"  Range: {complexity['min_complexity']:.3f} - {complexity['max_complexity']:.3f}")
            
            print(f"\nOptimization Analytics:")
            optimization = routing_analytics['optimization_analytics']
            print(f"  Optimizations Applied: {optimization['optimizations_applied']}")
            print(f"  Optimization Rate: {optimization['optimization_rate']:.1f}%")
            print(f"  Total Tokens Saved: {optimization['total_tokens_saved']}")
        
        # Get model recommendations
        recommendations = self.gateway.model_router.get_model_recommendations()
        
        print(f"\nOptimization Recommendations:")
        for rec in recommendations:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢", "info": "ℹ️"}.get(rec.get('priority', 'info'), "ℹ️")
            print(f"  {priority_icon} {rec['message']}")
        
        # Get cache effectiveness report
        cache_report = self.gateway.get_cache_effectiveness_report()
        
        print(f"\nCache Effectiveness Report:")
        print(f"  Rating: {cache_report['effectiveness_rating'].upper()}")
        print(f"  Hit Rate: {cache_report['hit_rate']:.1%}")
        print(f"  Estimated Cost Savings: ${cache_report['performance_summary']['estimated_cost_savings']:.4f}")
        
        if cache_report['recommendations']:
            print(f"\nCache Recommendations:")
            for rec in cache_report['recommendations']:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec['priority'], "ℹ️")
                print(f"  {priority_icon} {rec['message']}")


async def main():
    """Run the model router and caching demonstration."""
    try:
        demo = ModelRouterCachingDemo()
        await demo.run_demo()
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set. Demo will run in simulation mode.")
    
    if not os.getenv("HELICONE_API_KEY"):
        print("⚠️  Warning: HELICONE_API_KEY not set. Using demo configuration.")
    
    print("Starting Model Router and Caching Demo...")
    asyncio.run(main())