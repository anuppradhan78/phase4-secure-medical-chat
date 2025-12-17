"""
Mock LLM Gateway for testing when external services are not available.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, List

from ..models import ChatRequest, ChatResponse, UserRole


class MockCostTracker:
    """Mock cost tracker for testing."""
    
    def __init__(self):
        self.mock_data = []
    
    def get_cost_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_role: Optional[UserRole] = None
    ) -> Dict[str, Any]:
        """Mock cost summary."""
        return {
            "summary": {
                "total_cost_usd": 5.67,
                "total_requests": 45,
                "cache_hit_rate": 0.23,
                "avg_cost_per_request": 0.126
            }
        }


class MockLLMGateway:
    """Mock LLM Gateway for testing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_count = 0
        self.cost_tracker = MockCostTracker()
        self.logger.info("Mock LLM Gateway initialized")
    
    async def process_chat_request(
        self,
        request: ChatRequest,
        system_prompt: Optional[str] = None
    ) -> Tuple[ChatResponse, Dict[str, Any]]:
        """Process a mock chat request."""
        self.request_count += 1
        
        # Generate mock response based on message content
        message_lower = request.message.lower()
        
        if "chest pain" in message_lower or "difficulty breathing" in message_lower:
            response_text = (
                "I understand you're experiencing concerning symptoms. "
                "Chest pain and difficulty breathing can be serious. "
                "Please consider seeking immediate medical attention if these symptoms are severe. "
                "This is for informational purposes only. Consult your healthcare provider for medical advice."
            )
        elif "headache" in message_lower:
            response_text = (
                "Headaches can have various causes including stress, dehydration, tension, or other factors. "
                "If headaches are severe, persistent, or accompanied by other symptoms, "
                "it's important to consult with a healthcare provider. "
                "This is for informational purposes only. Consult your healthcare provider for medical advice."
            )
        elif "medication" in message_lower or "dosage" in message_lower:
            response_text = (
                "I cannot provide specific medication dosages or prescriptions. "
                "Only licensed healthcare providers can prescribe medications and determine appropriate dosages. "
                "Please consult your doctor or pharmacist for medication information."
            )
        else:
            response_text = (
                "Thank you for your question. For any health-related concerns, "
                "I recommend consulting with a qualified healthcare provider who can provide "
                "personalized medical advice based on your specific situation. "
                "This is for informational purposes only. Consult your healthcare provider for medical advice."
            )
        
        # Mock metadata
        metadata = {
            "cost": 0.002,  # Mock cost
            "latency_ms": 150,  # Mock latency
            "model_used": "mock-gpt-3.5-turbo",
            "cache_hit": False,
            "tokens_used": len(request.message.split()) + len(response_text.split()),
            "input_tokens": len(request.message.split()),
            "output_tokens": len(response_text.split()),
            "mock_service": True
        }
        
        return ChatResponse(
            response=response_text,
            metadata=metadata
        ), metadata
    
    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "overall": "healthy",
            "cost_tracker": "healthy",
            "mock_service": True,
            "requests_processed": self.request_count
        }
    
    def get_metrics(self, period_hours: int = 24) -> Dict[str, Any]:
        """Mock metrics."""
        return {
            "total_cost_usd": 15.67,
            "queries_today": 234,
            "cache_hit_rate": 0.23,
            "avg_latency_ms": 1100.0,
            "cost_by_model": {
                "gpt-3.5-turbo": 8.45,
                "gpt-4": 7.22
            },
            "cost_by_role": {
                "patient": 5.23,
                "physician": 8.91,
                "admin": 1.53
            },
            "security_events_today": 3,
            "mock_service": True
        }
    
    def get_detailed_analytics(self, period_days: int = 7) -> Dict[str, Any]:
        """Mock detailed analytics."""
        return {
            "period": {
                "start": (datetime.now(timezone.utc) - timedelta(days=period_days)).isoformat(),
                "end": datetime.now(timezone.utc).isoformat(),
                "days": period_days
            },
            "summary": {
                "total_cost_usd": 45.23,
                "total_requests": 567,
                "cache_hit_rate": 0.28,
                "avg_cost_per_request": 0.08
            },
            "daily_costs": [
                {"date": "2024-12-15", "total_cost": 6.78, "total_requests": 89},
                {"date": "2024-12-14", "total_cost": 5.43, "total_requests": 67},
                {"date": "2024-12-13", "total_cost": 7.89, "total_requests": 98}
            ],
            "trends": {
                "cost_trend": "stable",
                "usage_trend": "increasing",
                "efficiency_trend": "improving"
            },
            "mock_service": True
        }
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Mock optimization report."""
        return {
            "current_metrics": {
                "total_cost": 45.23,
                "total_requests": 567,
                "cache_hit_rate": 0.28,
                "avg_cost_per_request": 0.08
            },
            "recommendations": [
                {
                    "category": "model_optimization",
                    "priority": "high",
                    "title": "Reduce GPT-4 Usage for Simple Queries",
                    "description": "Consider routing simpler queries to GPT-3.5 to reduce costs",
                    "potential_savings": 12.45,
                    "implementation": "Improve query complexity analysis"
                },
                {
                    "category": "caching",
                    "priority": "medium", 
                    "title": "Improve Caching Strategy",
                    "description": "Cache hit rate is 28%. Increase cache TTL or improve cache key generation",
                    "potential_savings": 6.78,
                    "implementation": "Extend cache TTL and implement semantic similarity caching"
                }
            ],
            "total_potential_savings": 19.23,
            "mock_service": True
        }
    
    def get_expensive_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Mock expensive queries."""
        return [
            {
                "id": 1,
                "timestamp": "2024-12-16T10:30:00Z",
                "model": "gpt-4",
                "cost_usd": 0.045,
                "user_role": "physician",
                "total_tokens": 1500,
                "cache_hit": False
            },
            {
                "id": 2,
                "timestamp": "2024-12-16T09:15:00Z", 
                "model": "gpt-4",
                "cost_usd": 0.038,
                "user_role": "admin",
                "total_tokens": 1200,
                "cache_hit": False
            },
            {
                "id": 3,
                "timestamp": "2024-12-16T08:45:00Z",
                "model": "gpt-3.5-turbo",
                "cost_usd": 0.012,
                "user_role": "patient",
                "total_tokens": 800,
                "cache_hit": False
            }
        ]
    
    def check_budget_alert(
        self,
        budget_limit: float,
        period_hours: int = 24,
        user_role: Optional[UserRole] = None
    ) -> Dict[str, Any]:
        """Mock budget alert check."""
        current_cost = 15.67
        return {
            "budget_exceeded": current_cost >= budget_limit,
            "current_cost": current_cost,
            "budget_limit": budget_limit,
            "utilization_percent": (current_cost / budget_limit) * 100 if budget_limit > 0 else 0,
            "remaining_budget": max(0, budget_limit - current_cost),
            "period_hours": period_hours,
            "user_role": user_role.value if user_role else "all",
            "requests_in_period": 234,
            "mock_service": True
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Mock cache statistics."""
        return {
            "basic_stats": {
                "total_entries": 45,
                "cache_ttl_hours": 24,
                "memory_usage_estimate": 46080
            },
            "performance_stats": {
                "hit_rate": 0.23,
                "total_requests": 234,
                "cache_hits": 54,
                "cache_misses": 180,
                "evictions": 12
            },
            "content_analysis": {
                "age_distribution": {"<1h": 15, "1-6h": 20, "6-24h": 10, ">24h": 0},
                "model_distribution": {"gpt-3.5-turbo": 28, "gpt-4": 17},
                "role_distribution": {"patient": 20, "physician": 18, "admin": 7}
            },
            "effectiveness": {
                "cost_savings_estimate": 2.34,
                "token_savings_estimate": 12000
            },
            "mock_service": True
        }
    
    def clear_cache(self) -> Dict[str, Any]:
        """Mock cache clearing."""
        return {
            "entries_cleared": 45,
            "cache_stats_preserved": True,
            "message": "Successfully cleared 45 cache entries",
            "mock_service": True
        }