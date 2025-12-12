"""
Tests for enhanced model router and caching functionality.

This test suite verifies:
1. Query complexity analysis accuracy
2. Model routing decisions
3. Prompt optimization effectiveness
4. Cache hit rate tracking
5. Cache effectiveness metrics

Requirements: 3.2, 3.4, 3.6
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm.helicone_client import QueryComplexityAnalyzer, PromptOptimizer, ModelRouter
from llm.llm_gateway import LLMGateway
from models import UserRole, ChatRequest, ModelConfig


class TestQueryComplexityAnalyzer:
    """Test query complexity analysis functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = QueryComplexityAnalyzer()
    
    def test_simple_query_complexity(self):
        """Test complexity analysis for simple queries."""
        simple_query = "I have a headache. What should I do?"
        
        analysis = self.analyzer.analyze_complexity(simple_query)
        
        assert analysis['overall_score'] < 0.3  # Should be low complexity
        assert analysis['recommendation'] == "gpt-3.5-turbo"
        assert analysis['indicators']['word_count'] < 20
    
    def test_complex_medical_query(self):
        """Test complexity analysis for complex medical queries."""
        complex_query = """
        Please provide a differential diagnosis for a 45-year-old patient presenting with 
        acute onset chest pain, elevated troponins, and ST-segment changes on ECG. 
        Consider both cardiac and non-cardiac etiologies including myocardial infarction, 
        pulmonary embolism, aortic dissection, and pericarditis.
        """
        
        analysis = self.analyzer.analyze_complexity(complex_query)
        
        assert analysis['overall_score'] > 0.6  # Should be high complexity
        assert "gpt-4" in analysis['recommendation']
        assert analysis['indicators']['medical_terms_found']['advanced'] > 0
    
    def test_medical_terminology_detection(self):
        """Test detection of medical terminology by complexity level."""
        # Basic medical terms
        basic_query = "I have symptoms like fever and cough"
        basic_analysis = self.analyzer.analyze_complexity(basic_query)
        assert basic_analysis['indicators']['medical_terms_found']['basic'] > 0
        
        # Advanced medical terms
        advanced_query = "Patient shows signs of nephrotoxicity and hepatotoxicity"
        advanced_analysis = self.analyzer.analyze_complexity(advanced_query)
        assert advanced_analysis['indicators']['medical_terms_found']['advanced'] > 0
    
    def test_reasoning_complexity_detection(self):
        """Test detection of clinical reasoning indicators."""
        reasoning_query = "Consider differential diagnosis and rule out myocardial infarction"
        
        analysis = self.analyzer.analyze_complexity(reasoning_query)
        
        assert analysis['indicators']['reasoning_indicators'] > 0
        assert analysis['components']['reasoning'] > 0


class TestPromptOptimizer:
    """Test prompt optimization functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = PromptOptimizer()
    
    def test_redundant_phrase_removal(self):
        """Test removal of redundant conversational phrases."""
        verbose_query = "I would like to know if you could please tell me about chest pain"
        
        optimization = self.optimizer.optimize_prompt(verbose_query, UserRole.PATIENT)
        
        assert optimization['tokens_saved'] > 0
        assert optimization['should_use_optimized']
        assert "I would like to know" not in optimization['optimized_message']
    
    def test_medical_compression_for_physicians(self):
        """Test medical abbreviation compression for physicians."""
        medical_query = "Patient has elevated blood pressure and heart rate"
        
        optimization = self.optimizer.optimize_prompt(medical_query, UserRole.PHYSICIAN)
        
        # Should compress medical terms for physicians
        optimized = optimization['optimized_message']
        assert "BP" in optimized or "HR" in optimized
    
    def test_patient_query_preservation(self):
        """Test that patient queries preserve clarity over compression."""
        patient_query = "I have high blood pressure and fast heart rate"
        
        optimization = self.optimizer.optimize_prompt(patient_query, UserRole.PATIENT)
        
        # Should not aggressively compress for patients
        optimized = optimization['optimized_message']
        assert "blood pressure" in optimized  # Should preserve full terms
    
    def test_structure_optimization(self):
        """Test optimization of query structure."""
        multi_question = "What is diabetes? How is it treated? What are the symptoms?"
        
        optimization = self.optimizer.optimize_prompt(multi_question, UserRole.PATIENT)
        
        if optimization['should_use_optimized']:
            assert "Questions:" in optimization['optimized_message']


class TestModelRouter:
    """Test enhanced model routing functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.router = ModelRouter()
    
    def test_patient_model_restriction(self):
        """Test that patients are restricted to GPT-3.5."""
        complex_query = "Provide differential diagnosis for chest pain with elevated troponins"
        
        result = self.router.select_model(complex_query, UserRole.PATIENT)
        
        assert result['model_config'].model == "gpt-3.5-turbo"
        assert "Role restriction" in result['routing_decision']['routing_reason']
    
    def test_physician_complexity_routing(self):
        """Test complexity-based routing for physicians."""
        # Simple query should use GPT-3.5
        simple_query = "What is aspirin used for?"
        simple_result = self.router.select_model(simple_query, UserRole.PHYSICIAN)
        assert simple_result['model_config'].model == "gpt-3.5-turbo"
        
        # Complex query should use GPT-4
        complex_query = """
        Develop a comprehensive treatment protocol for a patient with chronic kidney disease 
        stage 4, diabetes mellitus type 2, and hypertension, considering drug interactions 
        and contraindications for nephrotoxic medications.
        """
        complex_result = self.router.select_model(complex_query, UserRole.PHYSICIAN)
        assert complex_result['model_config'].model == "gpt-4"
    
    def test_routing_decision_tracking(self):
        """Test that routing decisions are properly tracked."""
        initial_count = len(self.router.routing_history)
        
        query = "Test query for routing"
        self.router.select_model(query, UserRole.PHYSICIAN)
        
        assert len(self.router.routing_history) == initial_count + 1
        
        latest_decision = self.router.routing_history[-1]
        assert 'timestamp' in latest_decision
        assert 'complexity_score' in latest_decision
        assert 'selected_model' in latest_decision
    
    def test_routing_analytics(self):
        """Test routing analytics generation."""
        # Generate some routing decisions
        test_queries = [
            ("Simple query", UserRole.PATIENT),
            ("Complex differential diagnosis query", UserRole.PHYSICIAN),
            ("Moderate complexity query", UserRole.PHYSICIAN)
        ]
        
        for query, role in test_queries:
            self.router.select_model(query, role)
        
        analytics = self.router.get_routing_analytics(days=1)
        
        if "message" not in analytics:  # Has actual data
            assert 'model_usage' in analytics
            assert 'complexity_analytics' in analytics
            assert 'optimization_analytics' in analytics


class TestLLMGatewayCaching:
    """Test enhanced caching functionality in LLM Gateway."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock Helicone config to avoid API calls
        with patch('llm.llm_gateway.HeliconeClient'):
            self.gateway = LLMGateway()
    
    def test_cache_key_generation(self):
        """Test cache key generation for consistent caching."""
        messages1 = [{"role": "user", "content": "Test message"}]
        messages2 = [{"role": "user", "content": "Test message"}]
        
        key1 = self.gateway._generate_cache_key(messages1, UserRole.PATIENT)
        key2 = self.gateway._generate_cache_key(messages2, UserRole.PATIENT)
        
        assert key1 == key2  # Same messages should generate same key
        
        # Different role should generate different key
        key3 = self.gateway._generate_cache_key(messages1, UserRole.PHYSICIAN)
        assert key1 != key3
    
    def test_cache_hit_rate_tracking(self):
        """Test cache hit rate calculation and tracking."""
        # Initially no requests
        assert self.gateway.get_cache_hit_rate() == 0.0
        
        # Simulate cache miss
        self.gateway._cache_stats["total_requests"] = 10
        self.gateway._cache_stats["hits"] = 3
        self.gateway._cache_stats["misses"] = 7
        
        hit_rate = self.gateway.get_cache_hit_rate()
        assert hit_rate == 0.3  # 3/10 = 0.3
    
    def test_cache_response_storage(self):
        """Test cache response storage and retrieval."""
        cache_key = "test_key"
        response_data = {
            "content": "Test response",
            "model": "gpt-3.5-turbo",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Store response
        self.gateway._cache_response(cache_key, response_data)
        
        # Retrieve response
        cached = self.gateway._get_cached_response(cache_key)
        
        assert cached is not None
        assert cached["content"] == "Test response"
        assert "age_seconds" in cached
    
    def test_cache_expiration(self):
        """Test cache expiration based on TTL."""
        cache_key = "test_key"
        
        # Create expired cache entry
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        response_data = {
            "content": "Expired response",
            "model": "gpt-3.5-turbo",
            "timestamp": old_timestamp
        }
        
        self.gateway._response_cache[cache_key] = response_data
        
        # Should return None for expired entry
        cached = self.gateway._get_cached_response(cache_key)
        assert cached is None
        
        # Should be removed from cache
        assert cache_key not in self.gateway._response_cache
    
    def test_cache_effectiveness_report(self):
        """Test cache effectiveness report generation."""
        # Set up some cache statistics
        self.gateway._cache_stats = {
            "hits": 25,
            "misses": 75,
            "total_requests": 100,
            "evictions": 5,
            "cache_size_history": [],
            "hit_rate_history": []
        }
        
        report = self.gateway.get_cache_effectiveness_report()
        
        assert 'effectiveness_rating' in report
        assert 'hit_rate' in report
        assert 'performance_summary' in report
        assert 'recommendations' in report
        
        # With 25% hit rate, should be "good"
        assert report['hit_rate'] == 0.25
    
    def test_cache_cleanup_on_size_limit(self):
        """Test cache cleanup when size limit is exceeded."""
        # Fill cache beyond limit
        for i in range(1050):  # Exceeds 1000 limit
            cache_key = f"key_{i}"
            response_data = {
                "content": f"Response {i}",
                "model": "gpt-3.5-turbo",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self.gateway._response_cache[cache_key] = response_data
        
        # Trigger cleanup by adding one more
        self.gateway._cache_response("final_key", {
            "content": "Final response",
            "model": "gpt-3.5-turbo",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Should have cleaned up to under 1000 entries
        assert len(self.gateway._response_cache) <= 1000
        assert self.gateway._cache_stats["evictions"] > 0


class TestIntegration:
    """Integration tests for model router and caching together."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('llm.llm_gateway.HeliconeClient'):
            self.gateway = LLMGateway()
    
    def test_routing_with_optimization_integration(self):
        """Test integration of routing with prompt optimization."""
        verbose_query = "I would like to know if you could please tell me about diabetes treatment"
        
        routing_result = self.gateway.model_router.select_model(verbose_query, UserRole.PATIENT)
        
        # Should have optimization result
        assert 'optimization_result' in routing_result
        
        # Should track optimization in routing decision
        routing_decision = routing_result['routing_decision']
        assert 'optimization_applied' in routing_decision
        assert 'tokens_saved' in routing_decision
    
    def test_cache_with_routing_metadata(self):
        """Test that cache stores routing metadata correctly."""
        cache_key = "test_integration"
        
        # Simulate caching with routing metadata
        response_data = {
            "content": "Test response",
            "model": "gpt-3.5-turbo",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_role": "patient",
            "complexity_score": 0.3,
            "tokens_used": 150,
            "cost_usd": 0.002
        }
        
        self.gateway._cache_response(cache_key, response_data)
        
        # Get cache stats should include this metadata
        cache_stats = self.gateway.get_cache_stats()
        
        assert 'content_analysis' in cache_stats
        assert 'role_distribution' in cache_stats['content_analysis']
        assert 'total_cached_cost' in cache_stats['content_analysis']


# Pytest fixtures and test runners
@pytest.fixture
def complexity_analyzer():
    """Fixture for complexity analyzer."""
    return QueryComplexityAnalyzer()


@pytest.fixture
def prompt_optimizer():
    """Fixture for prompt optimizer."""
    return PromptOptimizer()


@pytest.fixture
def model_router():
    """Fixture for model router."""
    return ModelRouter()


@pytest.fixture
def llm_gateway():
    """Fixture for LLM gateway with mocked dependencies."""
    with patch('llm.llm_gateway.HeliconeClient'):
        return LLMGateway()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])