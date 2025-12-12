"""
Metrics API endpoints for cost tracking and analytics.

This module provides endpoints for:
- Real-time cost metrics
- Usage analytics
- Performance monitoring
- Cost optimization insights
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
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
        
        return {
            "queries": filtered_queries,
            "total_found": len(filtered_queries),
            "min_cost_threshold": min_cost,
            "period": "all_time"
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