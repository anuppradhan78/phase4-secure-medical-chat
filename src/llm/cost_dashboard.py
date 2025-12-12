"""
Cost dashboard service for displaying cost metrics and analytics.

This module provides:
- Real-time cost metrics for the /api/metrics endpoint
- Cost visualization data
- Performance analytics
- Budget monitoring dashboard
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

from .cost_tracker import CostTracker
from .helicone_client import HeliconeClient
try:
    from ..models import UserRole, MetricsResponse
except ImportError:
    # Handle case when running as script or in tests
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from models import UserRole, MetricsResponse


logger = logging.getLogger(__name__)


class CostDashboard:
    """
    Cost dashboard service for metrics and analytics display.
    
    This service provides:
    - Real-time cost metrics
    - Performance analytics
    - Cost optimization insights
    - Budget monitoring
    """
    
    def __init__(self, cost_tracker: CostTracker, helicone_client: HeliconeClient):
        """Initialize cost dashboard with tracker and client."""
        self.cost_tracker = cost_tracker
        self.helicone_client = helicone_client
    
    def get_metrics_response(
        self,
        period_hours: int = 24,
        user_role: Optional[UserRole] = None
    ) -> MetricsResponse:
        """
        Get metrics response for the /api/metrics endpoint.
        
        Args:
            period_hours: Time period for metrics (default: 24 hours)
            user_role: Optional user role filter
            
        Returns:
            MetricsResponse object with current metrics
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=period_hours)
        
        # Get cost summary from persistent storage
        cost_summary = self.cost_tracker.get_cost_summary(start_date, end_date, user_role)
        
        # Get additional metrics from Helicone client (in-memory cache)
        helicone_summary = self.helicone_client.get_cost_summary(start_date, end_date, user_role)
        
        # Combine data from both sources
        total_cost = cost_summary["summary"]["total_cost_usd"]
        total_requests = cost_summary["summary"]["total_requests"]
        cache_hit_rate = cost_summary["summary"]["cache_hit_rate"]
        
        # Calculate average latency (mock data for now - would come from audit logs)
        avg_latency_ms = self._calculate_avg_latency(start_date, end_date)
        
        # Get cost breakdowns
        cost_by_model = {}
        for model, data in cost_summary["breakdown"]["by_model"].items():
            cost_by_model[model] = data["cost"]
        
        cost_by_role = {}
        for role, data in cost_summary["breakdown"]["by_role"].items():
            cost_by_role[role] = data["cost"]
        
        # Get security events count (would integrate with security logging)
        security_events_today = self._get_security_events_count(start_date, end_date)
        
        return MetricsResponse(
            total_cost_usd=total_cost,
            queries_today=total_requests,
            cache_hit_rate=cache_hit_rate,
            avg_latency_ms=avg_latency_ms,
            cost_by_model=cost_by_model,
            cost_by_role=cost_by_role,
            security_events_today=security_events_today
        )
    
    def get_detailed_analytics(
        self,
        period_days: int = 7
    ) -> Dict[str, Any]:
        """
        Get detailed analytics for dashboard display.
        
        Args:
            period_days: Number of days for analysis
            
        Returns:
            Dict with detailed analytics data
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=period_days)
        
        # Get comprehensive cost summary
        cost_summary = self.cost_tracker.get_cost_summary(start_date, end_date)
        
        # Get daily breakdown
        daily_costs = self.cost_tracker.get_daily_costs(period_days)
        
        # Get role analytics
        role_analytics = self.cost_tracker.get_role_analytics()
        
        # Get expensive queries
        expensive_queries = self.cost_tracker.get_expensive_queries(limit=10)
        
        # Calculate trends
        trends = self._calculate_trends(daily_costs)
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": period_days
            },
            "summary": cost_summary["summary"],
            "breakdown": cost_summary["breakdown"],
            "optimization": cost_summary["optimization"],
            "daily_costs": daily_costs,
            "role_analytics": role_analytics,
            "expensive_queries": expensive_queries,
            "trends": trends,
            "performance": {
                "avg_latency_ms": self._calculate_avg_latency(start_date, end_date),
                "cache_effectiveness": self._analyze_cache_effectiveness(start_date, end_date),
                "model_performance": self._analyze_model_performance(start_date, end_date)
            }
        }
    
    def get_cost_optimization_report(self) -> Dict[str, Any]:
        """
        Generate cost optimization report with actionable insights.
        
        Returns:
            Dict with optimization recommendations and analysis
        """
        # Get last 7 days of data for analysis
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        cost_summary = self.cost_tracker.get_cost_summary(start_date, end_date)
        expensive_queries = self.cost_tracker.get_expensive_queries(limit=20)
        role_analytics = self.cost_tracker.get_role_analytics()
        
        # Analyze model usage efficiency
        model_efficiency = self._analyze_model_efficiency(cost_summary["breakdown"]["by_model"])
        
        # Analyze role-based spending patterns
        role_efficiency = self._analyze_role_efficiency(role_analytics)
        
        # Generate specific recommendations
        recommendations = []
        
        # Model optimization recommendations
        if model_efficiency["gpt4_overuse_score"] > 0.7:
            recommendations.append({
                "category": "model_optimization",
                "priority": "high",
                "title": "Reduce GPT-4 Usage for Simple Queries",
                "description": "High GPT-4 usage detected. Consider routing simpler queries to GPT-3.5.",
                "potential_savings": model_efficiency["potential_model_savings"],
                "implementation": "Improve query complexity analysis and model routing logic."
            })
        
        # Caching recommendations
        if cost_summary["summary"]["cache_hit_rate"] < 0.3:
            recommendations.append({
                "category": "caching",
                "priority": "medium",
                "title": "Improve Caching Strategy",
                "description": f"Cache hit rate is {cost_summary['summary']['cache_hit_rate']:.1%}. Increase cache TTL or improve cache key generation.",
                "potential_savings": cost_summary["summary"]["total_cost_usd"] * 0.15,
                "implementation": "Extend cache TTL and implement semantic similarity caching."
            })
        
        # Role-based recommendations
        for role, analytics in role_analytics.items():
            if analytics["avg_cost_per_request"] > 0.05:  # High cost per request
                recommendations.append({
                    "category": "role_optimization",
                    "priority": "medium",
                    "title": f"Optimize {role.title()} Query Costs",
                    "description": f"{role.title()} role has high average cost per request: ${analytics['avg_cost_per_request']:.3f}",
                    "potential_savings": analytics["total_cost"] * 0.2,
                    "implementation": f"Review {role} query patterns and implement role-specific optimizations."
                })
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "current_metrics": {
                "total_cost": cost_summary["summary"]["total_cost_usd"],
                "total_requests": cost_summary["summary"]["total_requests"],
                "cache_hit_rate": cost_summary["summary"]["cache_hit_rate"],
                "avg_cost_per_request": cost_summary["summary"]["avg_cost_per_request"]
            },
            "efficiency_analysis": {
                "model_efficiency": model_efficiency,
                "role_efficiency": role_efficiency,
                "cache_efficiency": {
                    "hit_rate": cost_summary["summary"]["cache_hit_rate"],
                    "potential_improvement": max(0, 0.5 - cost_summary["summary"]["cache_hit_rate"])
                }
            },
            "recommendations": recommendations,
            "total_potential_savings": sum(r.get("potential_savings", 0) for r in recommendations),
            "expensive_queries": expensive_queries[:5]  # Top 5 for focus
        }
    
    def _calculate_avg_latency(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate average latency (mock implementation)."""
        # In a real implementation, this would query audit logs for latency data
        # For now, return a reasonable mock value
        return 1250.0  # milliseconds
    
    def _get_security_events_count(self, start_date: datetime, end_date: datetime) -> int:
        """Get count of security events (mock implementation)."""
        # In a real implementation, this would query security logs
        # For now, return a mock value
        return 3
    
    def _calculate_trends(self, daily_costs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate cost and usage trends."""
        if len(daily_costs) < 2:
            return {"cost_trend": "stable", "usage_trend": "stable", "efficiency_trend": "stable"}
        
        # Calculate cost trend (last 3 days vs previous 3 days)
        recent_costs = daily_costs[:3]
        previous_costs = daily_costs[3:6] if len(daily_costs) >= 6 else daily_costs[3:]
        
        if not previous_costs:
            return {"cost_trend": "insufficient_data", "usage_trend": "insufficient_data", "efficiency_trend": "insufficient_data"}
        
        recent_avg_cost = sum(d["total_cost"] for d in recent_costs) / len(recent_costs)
        previous_avg_cost = sum(d["total_cost"] for d in previous_costs) / len(previous_costs)
        
        recent_avg_requests = sum(d["total_requests"] for d in recent_costs) / len(recent_costs)
        previous_avg_requests = sum(d["total_requests"] for d in previous_costs) / len(previous_costs)
        
        # Determine trends
        cost_change = (recent_avg_cost - previous_avg_cost) / previous_avg_cost if previous_avg_cost > 0 else 0
        usage_change = (recent_avg_requests - previous_avg_requests) / previous_avg_requests if previous_avg_requests > 0 else 0
        
        cost_trend = "increasing" if cost_change > 0.1 else "decreasing" if cost_change < -0.1 else "stable"
        usage_trend = "increasing" if usage_change > 0.1 else "decreasing" if usage_change < -0.1 else "stable"
        
        # Efficiency trend (cost per request)
        recent_efficiency = recent_avg_cost / recent_avg_requests if recent_avg_requests > 0 else 0
        previous_efficiency = previous_avg_cost / previous_avg_requests if previous_avg_requests > 0 else 0
        efficiency_change = (recent_efficiency - previous_efficiency) / previous_efficiency if previous_efficiency > 0 else 0
        
        efficiency_trend = "improving" if efficiency_change < -0.1 else "declining" if efficiency_change > 0.1 else "stable"
        
        return {
            "cost_trend": cost_trend,
            "cost_change_percent": cost_change * 100,
            "usage_trend": usage_trend,
            "usage_change_percent": usage_change * 100,
            "efficiency_trend": efficiency_trend,
            "efficiency_change_percent": efficiency_change * 100
        }
    
    def _analyze_cache_effectiveness(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze cache effectiveness."""
        cost_summary = self.cost_tracker.get_cost_summary(start_date, end_date)
        cache_hit_rate = cost_summary["summary"]["cache_hit_rate"]
        
        # Calculate potential savings from improved caching
        total_cost = cost_summary["summary"]["total_cost_usd"]
        current_savings = total_cost * cache_hit_rate  # Assuming cache hits save 100% of cost
        potential_additional_savings = total_cost * max(0, 0.5 - cache_hit_rate)  # Target 50% hit rate
        
        return {
            "current_hit_rate": cache_hit_rate,
            "target_hit_rate": 0.5,
            "current_savings": current_savings,
            "potential_additional_savings": potential_additional_savings,
            "effectiveness_score": min(cache_hit_rate / 0.5, 1.0)  # Score out of 1.0
        }
    
    def _analyze_model_performance(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze model performance and efficiency."""
        cost_summary = self.cost_tracker.get_cost_summary(start_date, end_date)
        model_breakdown = cost_summary["breakdown"]["by_model"]
        
        model_performance = {}
        for model, data in model_breakdown.items():
            avg_cost_per_request = data["cost"] / data["requests"] if data["requests"] > 0 else 0
            
            model_performance[model] = {
                "total_cost": data["cost"],
                "total_requests": data["requests"],
                "avg_cost_per_request": avg_cost_per_request,
                "cost_efficiency_score": self._calculate_model_efficiency_score(model, avg_cost_per_request)
            }
        
        return model_performance
    
    def _calculate_model_efficiency_score(self, model: str, avg_cost_per_request: float) -> float:
        """Calculate efficiency score for a model (0.0 to 1.0)."""
        # Define baseline costs for efficiency scoring
        baseline_costs = {
            "gpt-3.5-turbo": 0.002,
            "gpt-4": 0.02,
            "gpt-4-turbo": 0.01
        }
        
        baseline = baseline_costs.get(model, 0.01)
        
        # Score based on how close actual cost is to baseline
        if avg_cost_per_request <= baseline:
            return 1.0
        elif avg_cost_per_request <= baseline * 2:
            return 1.0 - ((avg_cost_per_request - baseline) / baseline)
        else:
            return 0.0
    
    def _analyze_model_efficiency(self, model_breakdown: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze model usage efficiency."""
        total_cost = sum(data["cost"] for data in model_breakdown.values())
        total_requests = sum(data["requests"] for data in model_breakdown.values())
        
        gpt4_data = model_breakdown.get("gpt-4", {"cost": 0, "requests": 0})
        gpt35_data = model_breakdown.get("gpt-3.5-turbo", {"cost": 0, "requests": 0})
        
        gpt4_cost_ratio = gpt4_data["cost"] / total_cost if total_cost > 0 else 0
        gpt4_request_ratio = gpt4_data["requests"] / total_requests if total_requests > 0 else 0
        
        # Calculate overuse score (high cost ratio relative to request ratio)
        gpt4_overuse_score = gpt4_cost_ratio / max(gpt4_request_ratio, 0.01) if gpt4_request_ratio > 0 else 0
        gpt4_overuse_score = min(gpt4_overuse_score / 10, 1.0)  # Normalize to 0-1
        
        # Estimate potential savings from better model routing
        potential_model_savings = 0
        if gpt4_overuse_score > 0.5:  # If GPT-4 is overused
            # Assume 30% of GPT-4 queries could use GPT-3.5 (90% cost reduction)
            potential_model_savings = gpt4_data["cost"] * 0.3 * 0.9
        
        return {
            "gpt4_cost_ratio": gpt4_cost_ratio,
            "gpt4_request_ratio": gpt4_request_ratio,
            "gpt4_overuse_score": gpt4_overuse_score,
            "potential_model_savings": potential_model_savings,
            "model_distribution": {
                model: {"cost_share": data["cost"] / total_cost if total_cost > 0 else 0,
                       "request_share": data["requests"] / total_requests if total_requests > 0 else 0}
                for model, data in model_breakdown.items()
            }
        }
    
    def _analyze_role_efficiency(self, role_analytics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze role-based spending efficiency."""
        role_efficiency = {}
        
        for role, analytics in role_analytics.items():
            avg_cost = analytics["avg_cost_per_request"]
            cache_hit_rate = analytics["cache_hit_rate"]
            
            # Define efficiency benchmarks by role
            benchmarks = {
                "patient": {"cost": 0.003, "cache_rate": 0.4},
                "physician": {"cost": 0.008, "cache_rate": 0.3},
                "admin": {"cost": 0.005, "cache_rate": 0.5}
            }
            
            benchmark = benchmarks.get(role, {"cost": 0.005, "cache_rate": 0.3})
            
            cost_efficiency = min(benchmark["cost"] / max(avg_cost, 0.001), 1.0)
            cache_efficiency = min(cache_hit_rate / benchmark["cache_rate"], 1.0)
            
            overall_efficiency = (cost_efficiency + cache_efficiency) / 2
            
            role_efficiency[role] = {
                "cost_efficiency": cost_efficiency,
                "cache_efficiency": cache_efficiency,
                "overall_efficiency": overall_efficiency,
                "avg_cost_per_request": avg_cost,
                "benchmark_cost": benchmark["cost"],
                "cache_hit_rate": cache_hit_rate,
                "benchmark_cache_rate": benchmark["cache_rate"]
            }
        
        return role_efficiency