"""
LLM Gateway with integrated cost tracking and optimization.

This module provides a unified interface for LLM interactions with:
- Helicone proxy integration
- Automatic cost tracking and storage
- Model routing and optimization
- Response caching
- Performance monitoring
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import json

from .helicone_client import HeliconeClient, ModelRouter, HeliconeConfig
from .cost_tracker import CostTracker
from .cost_dashboard import CostDashboard
from ..models import CostData, UserRole, ModelConfig, ChatRequest, ChatResponse


logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Unified LLM gateway with cost tracking and optimization.
    
    This gateway provides:
    - Transparent LLM access through Helicone
    - Automatic cost tracking and storage
    - Intelligent model routing
    - Response caching
    - Performance monitoring
    """
    
    def __init__(
        self,
        helicone_config: Optional[HeliconeConfig] = None,
        db_path: Optional[str] = None
    ):
        """Initialize LLM gateway with all components."""
        self.helicone_client = HeliconeClient(helicone_config)
        self.model_router = ModelRouter()
        self.cost_tracker = CostTracker(db_path)
        self.cost_dashboard = CostDashboard(self.cost_tracker, self.helicone_client)
        
        # Simple in-memory cache for responses
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 86400  # 24 hours
        
        logger.info("LLM Gateway initialized with cost tracking and optimization")
    
    async def process_chat_request(
        self,
        request: ChatRequest,
        system_prompt: Optional[str] = None
    ) -> Tuple[ChatResponse, Dict[str, Any]]:
        """
        Process a chat request with full cost tracking and optimization.
        
        Args:
            request: ChatRequest object
            system_prompt: Optional system prompt to prepend
            
        Returns:
            Tuple of (ChatResponse, metadata dict)
        """
        start_time = datetime.now(timezone.utc)
        
        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": request.message})
        
        # Check cache first
        cache_key = self._generate_cache_key(messages, request.user_role)
        cached_response = self._get_cached_response(cache_key)
        
        if cached_response:
            logger.info(f"Cache hit for request from {request.user_role.value}")
            
            # Still record the "cost" (which would be 0 for cache hits)
            cost_data = CostData(
                model=cached_response["model"],
                input_tokens=0,  # No tokens used for cache hit
                output_tokens=0,
                total_tokens=0,
                cost_usd=0.0,  # No cost for cache hit
                user_role=request.user_role,
                session_id=request.session_id,
                cache_hit=True
            )
            
            # Record the cache hit
            self.cost_tracker.record_cost(cost_data)
            
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            metadata = {
                "redaction_info": {"entities_redacted": 0, "entity_types": []},
                "cost": 0.0,
                "latency_ms": latency_ms,
                "model_used": cached_response["model"],
                "cache_hit": True,
                "security_flags": [],
                "tokens_used": 0
            }
            
            return ChatResponse(
                response=cached_response["content"],
                metadata=metadata
            ), metadata
        
        # Select appropriate model
        model_config = self.model_router.select_model(
            request.message,
            request.user_role
        )
        
        logger.info(
            f"Processing request with {model_config.model} for {request.user_role.value}"
        )
        
        try:
            # Make LLM request through Helicone
            llm_result = await self.helicone_client.chat_completion(
                messages=messages,
                model_config=model_config,
                user_role=request.user_role,
                session_id=request.session_id,
                user_id=request.user_id
            )
            
            response_content = llm_result["response"].choices[0].message.content
            cost_data = llm_result["cost_data"]
            
            # Store cost data persistently
            self.cost_tracker.record_cost(cost_data)
            
            # Cache the response
            self._cache_response(cache_key, {
                "content": response_content,
                "model": model_config.model,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Prepare metadata
            metadata = {
                "redaction_info": {"entities_redacted": 0, "entity_types": []},
                "cost": cost_data.cost_usd,
                "latency_ms": latency_ms,
                "model_used": model_config.model,
                "cache_hit": False,
                "security_flags": [],
                "tokens_used": cost_data.total_tokens,
                "input_tokens": cost_data.input_tokens,
                "output_tokens": cost_data.output_tokens
            }
            
            logger.info(
                f"Request completed: Cost=${cost_data.cost_usd:.4f}, "
                f"Latency={latency_ms}ms, Tokens={cost_data.total_tokens}"
            )
            
            return ChatResponse(
                response=response_content,
                metadata=metadata
            ), metadata
            
        except Exception as e:
            logger.error(f"Error processing chat request: {str(e)}")
            
            # Record failed request cost (minimal)
            error_cost_data = CostData(
                model=model_config.model,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                cost_usd=0.0,
                user_role=request.user_role,
                session_id=request.session_id,
                cache_hit=False
            )
            self.cost_tracker.record_cost(error_cost_data)
            
            raise
    
    def _generate_cache_key(self, messages: List[Dict[str, str]], user_role: UserRole) -> str:
        """Generate cache key for messages and user role."""
        # Create a hash of the messages and role for caching
        content = json.dumps(messages, sort_keys=True) + user_role.value
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired."""
        if cache_key not in self._response_cache:
            return None
        
        cached_item = self._response_cache[cache_key]
        cached_time = datetime.fromisoformat(cached_item["timestamp"])
        
        # Check if cache is expired
        if (datetime.now(timezone.utc) - cached_time).total_seconds() > self._cache_ttl_seconds:
            del self._response_cache[cache_key]
            return None
        
        return cached_item
    
    def _cache_response(self, cache_key: str, response_data: Dict[str, Any]):
        """Cache response data."""
        self._response_cache[cache_key] = response_data
        
        # Simple cache cleanup - remove oldest entries if cache gets too large
        if len(self._response_cache) > 1000:
            # Remove oldest 100 entries
            sorted_items = sorted(
                self._response_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            for key, _ in sorted_items[:100]:
                del self._response_cache[key]
    
    def get_metrics(self, period_hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive metrics for the specified period.
        
        Args:
            period_hours: Time period for metrics
            
        Returns:
            Dict with comprehensive metrics
        """
        return self.cost_dashboard.get_metrics_response(period_hours).dict()
    
    def get_detailed_analytics(self, period_days: int = 7) -> Dict[str, Any]:
        """
        Get detailed analytics for dashboard display.
        
        Args:
            period_days: Number of days for analysis
            
        Returns:
            Dict with detailed analytics
        """
        return self.cost_dashboard.get_detailed_analytics(period_days)
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """
        Get cost optimization report with recommendations.
        
        Returns:
            Dict with optimization analysis and recommendations
        """
        return self.cost_dashboard.get_cost_optimization_report()
    
    def get_expensive_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most expensive queries for optimization analysis.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of expensive queries with details
        """
        return self.cost_tracker.get_expensive_queries(limit)
    
    def clear_cache(self):
        """Clear response cache."""
        self._response_cache.clear()
        logger.info("Response cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._response_cache)
        
        # Calculate cache age distribution
        now = datetime.now(timezone.utc)
        age_buckets = {"<1h": 0, "1-6h": 0, "6-24h": 0, ">24h": 0}
        
        for cached_item in self._response_cache.values():
            cached_time = datetime.fromisoformat(cached_item["timestamp"])
            age_hours = (now - cached_time).total_seconds() / 3600
            
            if age_hours < 1:
                age_buckets["<1h"] += 1
            elif age_hours < 6:
                age_buckets["1-6h"] += 1
            elif age_hours < 24:
                age_buckets["6-24h"] += 1
            else:
                age_buckets[">24h"] += 1
        
        return {
            "total_entries": total_entries,
            "age_distribution": age_buckets,
            "cache_ttl_hours": self._cache_ttl_seconds / 3600,
            "memory_usage_estimate": total_entries * 1024  # Rough estimate in bytes
        }
    
    def set_cache_ttl(self, ttl_seconds: int):
        """Set cache TTL in seconds."""
        self._cache_ttl_seconds = ttl_seconds
        logger.info(f"Cache TTL set to {ttl_seconds} seconds")
    
    def check_budget_alert(
        self,
        budget_limit: float,
        period_hours: int = 24,
        user_role: Optional[UserRole] = None
    ) -> Dict[str, Any]:
        """
        Check if current spending exceeds budget limit.
        
        Args:
            budget_limit: Budget limit in USD
            period_hours: Time period for budget check
            user_role: Optional role filter
            
        Returns:
            Dict with budget status and details
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=period_hours)
        
        cost_summary = self.cost_tracker.get_cost_summary(start_date, end_date, user_role)
        current_cost = cost_summary["summary"]["total_cost_usd"]
        
        budget_exceeded = current_cost >= budget_limit
        utilization = current_cost / budget_limit if budget_limit > 0 else 0
        
        return {
            "budget_exceeded": budget_exceeded,
            "current_cost": current_cost,
            "budget_limit": budget_limit,
            "utilization_percent": utilization * 100,
            "remaining_budget": max(0, budget_limit - current_cost),
            "period_hours": period_hours,
            "user_role": user_role.value if user_role else "all",
            "requests_in_period": cost_summary["summary"]["total_requests"]
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of all gateway components.
        
        Returns:
            Dict with health status of all components
        """
        health_status = {
            "gateway": "healthy",
            "helicone_client": "unknown",
            "cost_tracker": "unknown",
            "cache": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Test cost tracker
            self.cost_tracker.get_cost_summary()
            health_status["cost_tracker"] = "healthy"
        except Exception as e:
            health_status["cost_tracker"] = f"error: {str(e)}"
        
        try:
            # Test cache
            cache_stats = self.get_cache_stats()
            health_status["cache"] = "healthy"
            health_status["cache_entries"] = cache_stats["total_entries"]
        except Exception as e:
            health_status["cache"] = f"error: {str(e)}"
        
        # Overall health
        component_statuses = [
            health_status["cost_tracker"],
            health_status["cache"]
        ]
        
        if all(status == "healthy" for status in component_statuses):
            health_status["overall"] = "healthy"
        elif any("error" in status for status in component_statuses):
            health_status["overall"] = "degraded"
        else:
            health_status["overall"] = "unknown"
        
        return health_status