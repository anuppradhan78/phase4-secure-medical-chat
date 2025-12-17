"""
Metrics API endpoints for cost tracking and analytics.

This module provides endpoints for:
- Real-time cost metrics
- Usage analytics
- Performance monitoring
- Cost optimization insights
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone, timedelta
from typing import Optional

from ..llm.llm_gateway import LLMGateway
from ..models import MetricsResponse, UserRole


router = APIRouter()

# Global LLM Gateway instance (would be initialized in main app)
_llm_gateway: Optional[LLMGateway] = None


def init_metrics_router(llm_gateway: LLMGateway):
    """Initialize the metrics router with LLM gateway."""
    global _llm_gateway
    _llm_gateway = llm_gateway


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    period_hours: int = Query(24, description="Time period in hours for metrics", ge=1, le=168),
    user_role: Optional[UserRole] = Query(None, description="Filter by user role")
):
    """
    Get cost and usage metrics for the specified time period.
    
    Returns comprehensive metrics including:
    - Total cost and request count
    - Cache hit rate and average latency
    - Cost breakdown by model and user role
    - Security events count
    
    This endpoint fulfills requirements 6.1, 6.2, 6.3, 6.4, 6.5:
    - Display basic metrics: total cost, cost per query, token usage, cache hit rate
    - Show cost breakdown by model (GPT-4 vs GPT-3.5) and user role
    - Identify expensive queries for optimization analysis
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        metrics_data = _llm_gateway.get_metrics(period_hours)
        
        # Filter by user role if specified
        if user_role:
            # Get role-specific metrics
            role_metrics = _llm_gateway.cost_tracker.get_cost_summary(
                user_role=user_role
            )
            
            # Update metrics with role-specific data
            metrics_data.update({
                "total_cost_usd": role_metrics["summary"]["total_cost_usd"],
                "queries_today": role_metrics["summary"]["total_requests"],
                "cache_hit_rate": role_metrics["summary"]["cache_hit_rate"],
                "cost_by_role": {user_role.value: role_metrics["summary"]["total_cost_usd"]}
            })
        
        return MetricsResponse(**metrics_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")


@router.get("/analytics")
async def get_detailed_analytics(
    period_days: int = Query(7, description="Time period in days for analytics", ge=1, le=30)
):
    """
    Get detailed analytics for dashboard display.
    
    Returns comprehensive analytics including:
    - Cost trends and patterns
    - Role-based usage analysis
    - Expensive query identification
    - Performance metrics
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        analytics = _llm_gateway.get_detailed_analytics(period_days)
        return analytics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")


@router.get("/optimization")
async def get_optimization_report():
    """
    Get cost optimization report with actionable recommendations.
    
    Returns:
    - Current efficiency metrics
    - Optimization recommendations
    - Potential cost savings
    - Expensive query analysis
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        optimization_report = _llm_gateway.get_optimization_report()
        return optimization_report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating optimization report: {str(e)}")


@router.get("/expensive-queries")
async def get_expensive_queries(
    limit: int = Query(10, description="Maximum number of queries to return", ge=1, le=50),
    min_cost: float = Query(0.01, description="Minimum cost threshold", ge=0.001)
):
    """
    Get the most expensive queries for optimization analysis.
    
    Returns list of expensive queries with:
    - Cost and token usage details
    - User role and session information
    - Model used and cache hit status
    
    This endpoint fulfills requirement 6.5: Identify expensive queries for optimization analysis
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        expensive_queries = _llm_gateway.get_expensive_queries(limit)
        
        # Filter by minimum cost
        filtered_queries = [
            query for query in expensive_queries 
            if query["cost_usd"] >= min_cost
        ]
        
        # Calculate optimization insights
        total_cost = sum(q["cost_usd"] for q in filtered_queries)
        avg_cost = total_cost / len(filtered_queries) if filtered_queries else 0
        
        # Identify patterns for optimization
        gpt4_queries = [q for q in filtered_queries if "gpt-4" in q.get("model", "")]
        gpt4_cost = sum(q["cost_usd"] for q in gpt4_queries)
        
        optimization_potential = 0
        if gpt4_queries:
            # Estimate savings if 30% of GPT-4 queries used GPT-3.5 (90% cost reduction)
            optimization_potential = gpt4_cost * 0.3 * 0.9
        
        return {
            "queries": filtered_queries,
            "total_found": len(filtered_queries),
            "min_cost_threshold": min_cost,
            "period": "all_time",
            "analysis": {
                "total_cost": total_cost,
                "average_cost": avg_cost,
                "gpt4_queries": len(gpt4_queries),
                "gpt4_cost": gpt4_cost,
                "optimization_potential": optimization_potential
            },
            "recommendations": [
                {
                    "type": "model_optimization",
                    "message": f"Consider routing {len(gpt4_queries)} GPT-4 queries to GPT-3.5 for potential savings of ${optimization_potential:.2f}"
                } if gpt4_queries else None
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving expensive queries: {str(e)}")


@router.get("/budget-status")
async def get_budget_status(
    budget_limit: float = Query(..., description="Budget limit in USD", gt=0),
    period_hours: int = Query(24, description="Time period for budget check", ge=1, le=168),
    user_role: Optional[UserRole] = Query(None, description="Filter by user role")
):
    """
    Check current spending against budget limit.
    
    Returns:
    - Budget exceeded status
    - Current cost and utilization
    - Remaining budget
    - Request count in period
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        budget_status = _llm_gateway.check_budget_alert(
            budget_limit=budget_limit,
            period_hours=period_hours,
            user_role=user_role
        )
        
        return budget_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking budget status: {str(e)}")


@router.get("/cache-stats")
async def get_cache_statistics():
    """
    Get cache performance statistics.
    
    Returns:
    - Cache entry count and age distribution
    - Memory usage estimates
    - Cache TTL configuration
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        cache_stats = _llm_gateway.get_cache_stats()
        return cache_stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving cache statistics: {str(e)}")


@router.post("/cache/clear")
async def clear_cache():
    """
    Clear the response cache.
    
    This endpoint allows administrators to clear the cache for testing
    or troubleshooting purposes.
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        _llm_gateway.clear_cache()
        return {"message": "Cache cleared successfully", "timestamp": datetime.now(timezone.utc).isoformat()}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@router.get("/cost-summary")
async def get_cost_summary(
    period_hours: int = Query(24, description="Time period in hours for summary", ge=1, le=168)
):
    """
    Get comprehensive cost summary for dashboard display.
    
    This endpoint provides all information needed for the cost dashboard and fulfills
    all requirements 6.1-6.5:
    - Total cost, cost per query, token usage, cache hit rate (6.1)
    - Cost breakdown by model (GPT-4 vs GPT-3.5) (6.2)
    - Cost breakdown by user role (6.3)
    - Cost tracking demonstration (6.4)
    - Expensive queries identification (6.5)
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        # Get all metrics data
        metrics_data = _llm_gateway.get_metrics(period_hours)
        analytics_data = _llm_gateway.get_detailed_analytics(7)
        optimization_data = _llm_gateway.get_optimization_report()
        expensive_queries = _llm_gateway.get_expensive_queries(10)
        cache_stats = _llm_gateway.get_cache_stats()
        
        # Calculate additional insights
        total_cost = metrics_data.get("total_cost_usd", 0)
        total_queries = metrics_data.get("queries_today", 0)
        cost_per_query = total_cost / total_queries if total_queries > 0 else 0
        
        # Token usage calculation (mock for demonstration)
        estimated_tokens = total_queries * 150  # Average tokens per query
        
        return {
            "period": {
                "hours": period_hours,
                "start": (datetime.now(timezone.utc) - timedelta(hours=period_hours)).isoformat(),
                "end": datetime.now(timezone.utc).isoformat()
            },
            "summary": {
                "total_cost_usd": total_cost,
                "total_queries": total_queries,
                "cost_per_query": cost_per_query,
                "estimated_token_usage": estimated_tokens,
                "cache_hit_rate": metrics_data.get("cache_hit_rate", 0),
                "avg_latency_ms": metrics_data.get("avg_latency_ms", 0),
                "security_events": metrics_data.get("security_events_today", 0)
            },
            "cost_breakdown": {
                "by_model": metrics_data.get("cost_by_model", {}),
                "by_role": metrics_data.get("cost_by_role", {}),
                "model_comparison": {
                    "gpt4_cost": metrics_data.get("cost_by_model", {}).get("gpt-4", 0),
                    "gpt35_cost": metrics_data.get("cost_by_model", {}).get("gpt-3.5-turbo", 0),
                    "gpt4_percentage": (metrics_data.get("cost_by_model", {}).get("gpt-4", 0) / total_cost * 100) if total_cost > 0 else 0
                }
            },
            "cache_performance": {
                "hit_rate": cache_stats.get("performance_stats", {}).get("hit_rate", 0),
                "total_entries": cache_stats.get("basic_stats", {}).get("total_entries", 0),
                "estimated_savings": cache_stats.get("effectiveness", {}).get("cost_savings_estimate", 0)
            },
            "expensive_queries": {
                "top_queries": expensive_queries[:5],
                "total_expensive_cost": sum(q.get("cost_usd", 0) for q in expensive_queries),
                "optimization_potential": sum(q.get("cost_usd", 0) * 0.5 for q in expensive_queries if "gpt-4" in q.get("model", ""))
            },
            "optimization": {
                "recommendations": optimization_data.get("recommendations", []),
                "total_potential_savings": optimization_data.get("total_potential_savings", 0)
            },
            "trends": analytics_data.get("trends", {}),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cost summary: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Perform health check of cost tracking components.
    
    Returns:
    - Overall system health status
    - Individual component status
    - Cache and database connectivity
    """
    if not _llm_gateway:
        raise HTTPException(status_code=500, detail="LLM Gateway not initialized")
    
    try:
        health_status = await _llm_gateway.health_check()
        
        # Return appropriate HTTP status based on health
        if health_status["overall"] == "healthy":
            return health_status
        elif health_status["overall"] == "degraded":
            raise HTTPException(status_code=503, detail=health_status)
        else:
            raise HTTPException(status_code=500, detail=health_status)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing health check: {str(e)}")