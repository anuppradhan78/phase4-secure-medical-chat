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
try:
    from ..models import CostData, UserRole, ModelConfig, ChatRequest, ChatResponse
except ImportError:
    # Handle case when running as script or in tests
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from models import CostData, UserRole, ModelConfig, ChatRequest, ChatResponse


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
        
        # Enhanced response cache with analytics
        self._response_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 86400  # 24 hours
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0,
            "cache_size_history": [],
            "hit_rate_history": []
        }
        
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
        
        # Check cache first with enhanced analytics
        cache_key = self._generate_cache_key(messages, request.user_role)
        cached_response = self._get_cached_response(cache_key)
        
        # Update cache statistics
        self._cache_stats["total_requests"] += 1
        
        if cached_response:
            self._cache_stats["hits"] += 1
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
                "tokens_used": 0,
                "cache_age_seconds": cached_response.get("age_seconds", 0)
            }
            
            return ChatResponse(
                response=cached_response["content"],
                metadata=metadata
            ), metadata
        
        # Cache miss
        self._cache_stats["misses"] += 1
        
        # Select appropriate model with enhanced routing
        routing_result = self.model_router.select_model(
            request.message,
            request.user_role
        )
        model_config = routing_result["model_config"]
        optimized_message = routing_result["optimized_message"]
        
        # Use optimized message for LLM request
        if optimized_message != request.message:
            messages[-1]["content"] = optimized_message  # Replace user message with optimized version
        
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
            
            # Cache the response with enhanced metadata
            self._cache_response(cache_key, {
                "content": response_content,
                "model": model_config.model,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user_role": request.user_role.value,
                "complexity_score": routing_result["complexity_analysis"]["overall_score"],
                "tokens_used": cost_data.total_tokens,
                "cost_usd": cost_data.cost_usd
            })
            
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Prepare enhanced metadata
            metadata = {
                "redaction_info": {"entities_redacted": 0, "entity_types": []},
                "cost": cost_data.cost_usd,
                "latency_ms": latency_ms,
                "model_used": model_config.model,
                "cache_hit": False,
                "security_flags": [],
                "tokens_used": cost_data.total_tokens,
                "input_tokens": cost_data.input_tokens,
                "output_tokens": cost_data.output_tokens,
                "complexity_analysis": routing_result["complexity_analysis"],
                "optimization_applied": routing_result["optimization_result"] is not None,
                "tokens_saved": routing_result["optimization_result"]["tokens_saved"] if routing_result["optimization_result"] else 0,
                "routing_decision": routing_result["routing_decision"]
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
        age_seconds = (datetime.now(timezone.utc) - cached_time).total_seconds()
        
        # Check if cache is expired
        if age_seconds > self._cache_ttl_seconds:
            del self._response_cache[cache_key]
            self._cache_stats["evictions"] += 1
            return None
        
        # Add age information to cached item
        cached_item["age_seconds"] = int(age_seconds)
        return cached_item
    
    def _cache_response(self, cache_key: str, response_data: Dict[str, Any]):
        """Cache response data with enhanced management."""
        self._response_cache[cache_key] = response_data
        
        # Record cache size for analytics
        current_size = len(self._response_cache)
        self._cache_stats["cache_size_history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "size": current_size
        })
        
        # Keep only last 100 size measurements
        if len(self._cache_stats["cache_size_history"]) > 100:
            self._cache_stats["cache_size_history"] = self._cache_stats["cache_size_history"][-100:]
        
        # Enhanced cache cleanup - remove oldest entries if cache gets too large
        if current_size > 1000:
            # Remove oldest 100 entries
            sorted_items = sorted(
                self._response_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            evicted_count = 0
            for key, _ in sorted_items[:100]:
                del self._response_cache[key]
                evicted_count += 1
            
            self._cache_stats["evictions"] += evicted_count
            logger.info(f"Cache cleanup: evicted {evicted_count} entries, new size: {len(self._response_cache)}")
        
        # Update hit rate history periodically
        if self._cache_stats["total_requests"] % 10 == 0:  # Every 10 requests
            hit_rate = self.get_cache_hit_rate()
            self._cache_stats["hit_rate_history"].append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "hit_rate": hit_rate,
                "total_requests": self._cache_stats["total_requests"]
            })
            
            # Keep only last 100 hit rate measurements
            if len(self._cache_stats["hit_rate_history"]) > 100:
                self._cache_stats["hit_rate_history"] = self._cache_stats["hit_rate_history"][-100:]
    
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
        """Clear response cache and reset statistics."""
        entries_cleared = len(self._response_cache)
        self._response_cache.clear()
        
        # Reset cache statistics but preserve historical data
        self._cache_stats["evictions"] += entries_cleared
        
        logger.info(f"Response cache cleared: {entries_cleared} entries removed")
        
        return {
            "entries_cleared": entries_cleared,
            "cache_stats_preserved": True,
            "message": f"Successfully cleared {entries_cleared} cache entries"
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_entries = len(self._response_cache)
        
        # Calculate cache age distribution
        now = datetime.now(timezone.utc)
        age_buckets = {"<1h": 0, "1-6h": 0, "6-24h": 0, ">24h": 0}
        
        # Enhanced cache analysis
        total_cached_cost = 0.0
        total_cached_tokens = 0
        model_distribution = {}
        role_distribution = {}
        
        for cached_item in self._response_cache.values():
            cached_time = datetime.fromisoformat(cached_item["timestamp"])
            age_hours = (now - cached_time).total_seconds() / 3600
            
            # Age distribution
            if age_hours < 1:
                age_buckets["<1h"] += 1
            elif age_hours < 6:
                age_buckets["1-6h"] += 1
            elif age_hours < 24:
                age_buckets["6-24h"] += 1
            else:
                age_buckets[">24h"] += 1
            
            # Cost and token analysis
            if "cost_usd" in cached_item:
                total_cached_cost += cached_item["cost_usd"]
            if "tokens_used" in cached_item:
                total_cached_tokens += cached_item["tokens_used"]
            
            # Model distribution
            model = cached_item.get("model", "unknown")
            model_distribution[model] = model_distribution.get(model, 0) + 1
            
            # Role distribution
            role = cached_item.get("user_role", "unknown")
            role_distribution[role] = role_distribution.get(role, 0) + 1
        
        # Calculate hit rate and effectiveness
        hit_rate = self.get_cache_hit_rate()
        
        return {
            "basic_stats": {
                "total_entries": total_entries,
                "cache_ttl_hours": self._cache_ttl_seconds / 3600,
                "memory_usage_estimate": total_entries * 1024  # Rough estimate in bytes
            },
            "performance_stats": {
                "hit_rate": hit_rate,
                "total_requests": self._cache_stats["total_requests"],
                "cache_hits": self._cache_stats["hits"],
                "cache_misses": self._cache_stats["misses"],
                "evictions": self._cache_stats["evictions"]
            },
            "content_analysis": {
                "age_distribution": age_buckets,
                "model_distribution": model_distribution,
                "role_distribution": role_distribution,
                "total_cached_cost": total_cached_cost,
                "total_cached_tokens": total_cached_tokens
            },
            "effectiveness": {
                "cost_savings_estimate": self._cache_stats["hits"] * (total_cached_cost / max(total_entries, 1)),
                "token_savings_estimate": self._cache_stats["hits"] * (total_cached_tokens / max(total_entries, 1)),
                "avg_cache_age_hours": self._calculate_avg_cache_age()
            },
            "trends": {
                "hit_rate_history": self._cache_stats["hit_rate_history"][-10:],  # Last 10 measurements
                "cache_size_history": self._cache_stats["cache_size_history"][-10:]  # Last 10 measurements
            }
        }
    
    def get_cache_hit_rate(self) -> float:
        """Calculate current cache hit rate."""
        total_requests = self._cache_stats["total_requests"]
        if total_requests == 0:
            return 0.0
        return self._cache_stats["hits"] / total_requests
    
    def _calculate_avg_cache_age(self) -> float:
        """Calculate average age of cached items in hours."""
        if not self._response_cache:
            return 0.0
        
        now = datetime.now(timezone.utc)
        total_age = 0.0
        
        for cached_item in self._response_cache.values():
            cached_time = datetime.fromisoformat(cached_item["timestamp"])
            age_hours = (now - cached_time).total_seconds() / 3600
            total_age += age_hours
        
        return total_age / len(self._response_cache)
    
    def get_cache_effectiveness_report(self) -> Dict[str, Any]:
        """Generate comprehensive cache effectiveness report."""
        stats = self.get_cache_stats()
        hit_rate = stats["performance_stats"]["hit_rate"]
        
        # Determine effectiveness level
        if hit_rate >= 0.4:
            effectiveness = "excellent"
        elif hit_rate >= 0.25:
            effectiveness = "good"
        elif hit_rate >= 0.15:
            effectiveness = "moderate"
        else:
            effectiveness = "poor"
        
        # Generate recommendations
        recommendations = []
        
        if hit_rate < 0.2:
            recommendations.append({
                "type": "cache_optimization",
                "priority": "high",
                "message": f"Low cache hit rate ({hit_rate:.1%}). Consider increasing cache TTL or improving cache key generation.",
                "action": "Analyze query patterns for better caching strategy"
            })
        
        if stats["basic_stats"]["total_entries"] < 50 and self._cache_stats["total_requests"] > 100:
            recommendations.append({
                "type": "cache_size",
                "priority": "medium",
                "message": "Low cache utilization. Queries may be too diverse for effective caching.",
                "action": "Review query similarity and cache key strategy"
            })
        
        # Calculate potential savings
        estimated_cost_per_request = 0.002  # Rough estimate for GPT-3.5
        potential_savings = self._cache_stats["hits"] * estimated_cost_per_request
        
        return {
            "effectiveness_rating": effectiveness,
            "hit_rate": hit_rate,
            "performance_summary": {
                "total_requests": self._cache_stats["total_requests"],
                "cache_hits": self._cache_stats["hits"],
                "estimated_cost_savings": potential_savings,
                "estimated_latency_improvement": f"{self._cache_stats['hits'] * 800}ms saved"  # Rough estimate
            },
            "recommendations": recommendations,
            "detailed_stats": stats
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