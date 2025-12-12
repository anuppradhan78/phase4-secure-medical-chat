"""
Tests for Helicone integration and cost tracking functionality.
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.llm.helicone_client import HeliconeClient, HeliconeConfig, ModelRouter
from src.llm.cost_tracker import CostTracker
from src.llm.cost_dashboard import CostDashboard
from src.llm.llm_gateway import LLMGateway
from src.models import CostData, UserRole, ModelConfig, ChatRequest


class TestHeliconeClient:
    """Test Helicone client functionality."""
    
    def test_config_from_env(self):
        """Test loading configuration from environment variables."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-openai-key',
            'HELICONE_API_KEY': 'test-key',
            'HELICONE_BASE_URL': 'https://test.example.com',
            'HELICONE_ENABLE_CACHING': 'true'
        }):
            client = HeliconeClient()
            assert client.config.api_key == 'test-key'
            assert client.config.base_url == 'https://test.example.com'
            assert client.config.enable_caching is True
    
    def test_config_missing_api_key(self):
        """Test error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="HELICONE_API_KEY"):
                HeliconeClient()
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-openai-key'})
    def test_calculate_cost(self):
        """Test cost calculation for different models."""
        config = HeliconeConfig(api_key="test-key")
        client = HeliconeClient(config)
        
        # Test GPT-3.5 cost calculation
        cost_data = client._calculate_cost(
            model="gpt-3.5-turbo",
            input_tokens=1000,
            output_tokens=500,
            user_role=UserRole.PATIENT
        )
        
        expected_cost = (1000 / 1000 * 0.0015) + (500 / 1000 * 0.002)
        assert abs(cost_data.cost_usd - expected_cost) < 0.0001
        assert cost_data.model == "gpt-3.5-turbo"
        assert cost_data.user_role == UserRole.PATIENT
        assert cost_data.total_tokens == 1500
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-openai-key'})
    def test_cost_summary_empty(self):
        """Test cost summary with no data."""
        config = HeliconeConfig(api_key="test-key")
        client = HeliconeClient(config)
        
        summary = client.get_cost_summary()
        
        assert summary["total_cost_usd"] == 0.0
        assert summary["total_requests"] == 0
        assert summary["cache_hit_rate"] == 0.0
        assert summary["cost_by_model"] == {}
        assert summary["cost_by_role"] == {}


class TestModelRouter:
    """Test model routing functionality."""
    
    def test_patient_always_gets_gpt35(self):
        """Test that patients always get GPT-3.5."""
        router = ModelRouter()
        
        # Simple message
        config = router.select_model("I have a headache", UserRole.PATIENT)
        assert config.model == "gpt-3.5-turbo"
        
        # Complex message
        config = router.select_model(
            "I need a detailed differential diagnosis for my complex symptoms",
            UserRole.PATIENT
        )
        assert config.model == "gpt-3.5-turbo"
    
    def test_physician_model_routing(self):
        """Test physician model routing based on complexity."""
        router = ModelRouter()
        
        # Simple message should get GPT-3.5
        config = router.select_model("What is aspirin?", UserRole.PHYSICIAN)
        assert config.model == "gpt-3.5-turbo"
        
        # Complex message should get GPT-4
        complex_message = (
            "Please provide a comprehensive differential diagnosis for a 65-year-old "
            "patient presenting with chest pain, shortness of breath, and elevated "
            "troponins. Consider all possible cardiac and non-cardiac causes."
        )
        config = router.select_model(complex_message, UserRole.PHYSICIAN, complexity_threshold=0.3)
        assert config.model == "gpt-4"
    
    def test_complexity_analysis(self):
        """Test complexity analysis algorithm."""
        router = ModelRouter()
        
        # Simple message
        simple_score = router._analyze_complexity("What is aspirin?")
        assert simple_score < 0.5
        
        # Complex message with medical terms
        complex_message = (
            "What are the differential diagnoses for acute chest pain in a patient "
            "with a history of coronary artery disease? Please provide detailed "
            "treatment recommendations and research-based evidence."
        )
        complex_score = router._analyze_complexity(complex_message)
        assert complex_score > 0.5


class TestCostTracker:
    """Test cost tracking functionality."""
    
    def test_record_and_retrieve_cost(self):
        """Test recording and retrieving cost data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            tracker = CostTracker(tmp_file.name)
            
            # Record cost data
            cost_data = CostData(
                model="gpt-3.5-turbo",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.0003,
                user_role=UserRole.PATIENT,
                session_id="test_session"
            )
            
            record_id = tracker.record_cost(cost_data)
            assert record_id > 0
            
            # Retrieve summary
            summary = tracker.get_cost_summary()
            assert summary["summary"]["total_cost_usd"] == 0.0003
            assert summary["summary"]["total_requests"] == 1
            assert summary["breakdown"]["by_model"]["gpt-3.5-turbo"]["cost"] == 0.0003
            assert summary["breakdown"]["by_role"]["patient"]["cost"] == 0.0003
    
    def test_expensive_queries(self):
        """Test expensive query tracking."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            tracker = CostTracker(tmp_file.name)
            
            # Record multiple cost entries
            costs = [0.001, 0.05, 0.002, 0.1, 0.003]
            for i, cost in enumerate(costs):
                cost_data = CostData(
                    model="gpt-4",
                    input_tokens=1000,
                    output_tokens=500,
                    total_tokens=1500,
                    cost_usd=cost,
                    user_role=UserRole.PHYSICIAN,
                    session_id=f"session_{i}"
                )
                tracker.record_cost(cost_data)
            
            # Get expensive queries
            expensive = tracker.get_expensive_queries(limit=3, min_cost=0.01)
            assert len(expensive) == 2  # Only 2 queries above 0.01
            assert expensive[0]["cost_usd"] == 0.1  # Highest cost first
            assert expensive[1]["cost_usd"] == 0.05


class TestCostDashboard:
    """Test cost dashboard functionality."""
    
    def test_metrics_response(self):
        """Test metrics response generation."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            tracker = CostTracker(tmp_file.name)
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-openai-key'}):
                config = HeliconeConfig(api_key="test-key")
                client = HeliconeClient(config)
                dashboard = CostDashboard(tracker, client)
            
            # Record some test data
            cost_data = CostData(
                model="gpt-3.5-turbo",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
                cost_usd=0.0003,
                user_role=UserRole.PATIENT
            )
            tracker.record_cost(cost_data)
            
            # Get metrics
            metrics = dashboard.get_metrics_response(period_hours=24)
            
            assert metrics.total_cost_usd == 0.0003
            assert metrics.queries_today == 1
            assert "gpt-3.5-turbo" in metrics.cost_by_model
            assert "patient" in metrics.cost_by_role


class TestLLMGateway:
    """Test LLM gateway integration."""
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-openai-key', 'HELICONE_API_KEY': 'test-helicone-key'})
    def test_cache_key_generation(self):
        """Test cache key generation."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            gateway = LLMGateway(db_path=tmp_file.name)
            
            messages1 = [{"role": "user", "content": "Hello"}]
            messages2 = [{"role": "user", "content": "Hello"}]
            messages3 = [{"role": "user", "content": "Hi"}]
            
            key1 = gateway._generate_cache_key(messages1, UserRole.PATIENT)
            key2 = gateway._generate_cache_key(messages2, UserRole.PATIENT)
            key3 = gateway._generate_cache_key(messages3, UserRole.PATIENT)
            key4 = gateway._generate_cache_key(messages1, UserRole.PHYSICIAN)
            
            assert key1 == key2  # Same messages and role
            assert key1 != key3  # Different message
            assert key1 != key4  # Different role
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-openai-key', 'HELICONE_API_KEY': 'test-helicone-key'})
    def test_cache_operations(self):
        """Test cache storage and retrieval."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            gateway = LLMGateway(db_path=tmp_file.name)
            
            # Cache a response
            cache_key = "test_key"
            response_data = {
                "content": "Test response",
                "model": "gpt-3.5-turbo",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            gateway._cache_response(cache_key, response_data)
            
            # Retrieve cached response
            cached = gateway._get_cached_response(cache_key)
            assert cached is not None
            assert cached["content"] == "Test response"
            
            # Test cache expiration (mock old timestamp)
            old_response = {
                "content": "Old response",
                "model": "gpt-3.5-turbo",
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            }
            gateway._cache_response("old_key", old_response)
            
            # Should return None for expired cache
            expired = gateway._get_cached_response("old_key")
            assert expired is None
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-openai-key', 'HELICONE_API_KEY': 'test-helicone-key'})
    def test_budget_alert(self):
        """Test budget alert functionality."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            gateway = LLMGateway(db_path=tmp_file.name)
            
            # Record some costs
            cost_data = CostData(
                model="gpt-4",
                input_tokens=1000,
                output_tokens=500,
                total_tokens=1500,
                cost_usd=0.05,
                user_role=UserRole.PHYSICIAN
            )
            gateway.cost_tracker.record_cost(cost_data)
            
            # Test budget check
            budget_status = gateway.check_budget_alert(
                budget_limit=0.03,  # Lower than actual cost
                period_hours=24
            )
            
            assert budget_status["budget_exceeded"] is True
            assert budget_status["current_cost"] == 0.05
            assert budget_status["utilization_percent"] > 100
            
            # Test budget not exceeded
            budget_status = gateway.check_budget_alert(
                budget_limit=0.10,  # Higher than actual cost
                period_hours=24
            )
            
            assert budget_status["budget_exceeded"] is False
            assert budget_status["remaining_budget"] == 0.05


@pytest.mark.asyncio
@patch.dict(os.environ, {'OPENAI_API_KEY': 'test-openai-key', 'HELICONE_API_KEY': 'test-helicone-key'})
async def test_health_check():
    """Test gateway health check."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        gateway = LLMGateway(db_path=tmp_file.name)
        
        health = await gateway.health_check()
        
        assert "gateway" in health
        assert "cost_tracker" in health
        assert "cache" in health
        assert "overall" in health
        assert "timestamp" in health


if __name__ == "__main__":
    pytest.main([__file__])