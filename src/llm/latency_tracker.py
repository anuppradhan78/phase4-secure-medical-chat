"""
Latency tracking and optimization service.

This module provides comprehensive latency measurement and analysis for the
secure medical chat system, including breakdown by pipeline stages and
optimization recommendations.
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import statistics
import json

logger = logging.getLogger(__name__)


@dataclass
class LatencyMeasurement:
    """Individual latency measurement for a pipeline stage."""
    stage_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, metadata: Optional[Dict[str, Any]] = None):
        """Mark the measurement as complete."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        if metadata:
            self.metadata.update(metadata)


@dataclass
class RequestLatencyProfile:
    """Complete latency profile for a request."""
    request_id: str
    user_role: str
    model_used: str
    total_duration_ms: float
    stages: List[LatencyMeasurement]
    timestamp: datetime
    cache_hit: bool = False
    optimization_applied: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_stage_duration(self, stage_name: str) -> Optional[float]:
        """Get duration for a specific stage."""
        for stage in self.stages:
            if stage.stage_name == stage_name:
                return stage.duration_ms
        return None
    
    def get_breakdown_percentages(self) -> Dict[str, float]:
        """Get percentage breakdown of time spent in each stage."""
        if self.total_duration_ms == 0:
            return {}
        
        breakdown = {}
        for stage in self.stages:
            if stage.duration_ms is not None:
                percentage = (stage.duration_ms / self.total_duration_ms) * 100
                breakdown[stage.stage_name] = round(percentage, 2)
        
        return breakdown


class LatencyTracker:
    """
    Service for tracking and analyzing latency across the chat pipeline.
    
    Provides:
    - Real-time latency measurement
    - Historical latency analysis
    - Performance optimization recommendations
    - Latency breakdown by pipeline stages
    """
    
    def __init__(self, max_history: int = 1000):
        """Initialize latency tracker."""
        self.max_history = max_history
        self.request_profiles: List[RequestLatencyProfile] = []
        self.active_measurements: Dict[str, List[LatencyMeasurement]] = {}
        
        # Performance baselines (in milliseconds)
        self.performance_baselines = {
            "authentication": 5,
            "rate_limiting": 3,
            "pii_redaction": 100,
            "guardrails_validation": 150,
            "medical_safety": 50,
            "llm_processing": 2000,  # Varies significantly by model
            "response_validation": 50,
            "de_anonymization": 30,
            "audit_logging": 20,
            "total_request": 2500
        }
        
        # Model-specific baselines
        self.model_baselines = {
            "gpt-3.5-turbo": {"llm_processing": 1500, "total_request": 2000},
            "gpt-4": {"llm_processing": 3000, "total_request": 4000},
            "gpt-4-turbo": {"llm_processing": 2000, "total_request": 2800}
        }
        
        logger.info("Latency tracker initialized")
    
    @contextmanager
    def measure_stage(self, request_id: str, stage_name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager for measuring individual pipeline stages.
        
        Usage:
            with latency_tracker.measure_stage(request_id, "pii_redaction"):
                # Perform PII redaction
                pass
        """
        measurement = LatencyMeasurement(
            stage_name=stage_name,
            start_time=time.perf_counter(),
            metadata=metadata or {}
        )
        
        # Initialize request tracking if needed
        if request_id not in self.active_measurements:
            self.active_measurements[request_id] = []
        
        self.active_measurements[request_id].append(measurement)
        
        try:
            yield measurement
        finally:
            measurement.finish()
    
    def start_request_tracking(self, request_id: str) -> float:
        """Start tracking a complete request."""
        start_time = time.perf_counter()
        self.active_measurements[request_id] = []
        return start_time
    
    def finish_request_tracking(
        self,
        request_id: str,
        start_time: float,
        user_role: str,
        model_used: str,
        cache_hit: bool = False,
        optimization_applied: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RequestLatencyProfile:
        """Complete request tracking and store the profile."""
        end_time = time.perf_counter()
        total_duration_ms = (end_time - start_time) * 1000
        
        stages = self.active_measurements.get(request_id, [])
        
        profile = RequestLatencyProfile(
            request_id=request_id,
            user_role=user_role,
            model_used=model_used,
            total_duration_ms=total_duration_ms,
            stages=stages,
            timestamp=datetime.now(timezone.utc),
            cache_hit=cache_hit,
            optimization_applied=optimization_applied,
            metadata=metadata or {}
        )
        
        # Store profile and clean up active tracking
        self.request_profiles.append(profile)
        if request_id in self.active_measurements:
            del self.active_measurements[request_id]
        
        # Maintain history limit
        if len(self.request_profiles) > self.max_history:
            self.request_profiles = self.request_profiles[-self.max_history:]
        
        logger.debug(f"Request {request_id} completed in {total_duration_ms:.2f}ms")
        
        return profile
    
    def get_latency_analytics(self, period_hours: int = 24) -> Dict[str, Any]:
        """
        Get comprehensive latency analytics for the specified period.
        
        Args:
            period_hours: Time period for analysis
            
        Returns:
            Dict with detailed latency analytics
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=period_hours)
        recent_profiles = [
            p for p in self.request_profiles 
            if p.timestamp >= cutoff_time
        ]
        
        if not recent_profiles:
            return {
                "period_hours": period_hours,
                "total_requests": 0,
                "message": "No requests in the specified period"
            }
        
        # Overall statistics
        total_latencies = [p.total_duration_ms for p in recent_profiles]
        cache_hits = [p for p in recent_profiles if p.cache_hit]
        cache_misses = [p for p in recent_profiles if not p.cache_hit]
        
        analytics = {
            "period_hours": period_hours,
            "total_requests": len(recent_profiles),
            "overall_stats": {
                "avg_latency_ms": round(statistics.mean(total_latencies), 2),
                "median_latency_ms": round(statistics.median(total_latencies), 2),
                "p95_latency_ms": round(self._percentile(total_latencies, 95), 2),
                "p99_latency_ms": round(self._percentile(total_latencies, 99), 2),
                "min_latency_ms": round(min(total_latencies), 2),
                "max_latency_ms": round(max(total_latencies), 2)
            },
            "cache_performance": {
                "cache_hit_rate": len(cache_hits) / len(recent_profiles),
                "avg_cache_hit_latency_ms": round(statistics.mean([p.total_duration_ms for p in cache_hits]), 2) if cache_hits else 0,
                "avg_cache_miss_latency_ms": round(statistics.mean([p.total_duration_ms for p in cache_misses]), 2) if cache_misses else 0,
                "cache_speedup_factor": 0
            }
        }
        
        # Calculate cache speedup
        if cache_hits and cache_misses:
            cache_hit_avg = statistics.mean([p.total_duration_ms for p in cache_hits])
            cache_miss_avg = statistics.mean([p.total_duration_ms for p in cache_misses])
            analytics["cache_performance"]["cache_speedup_factor"] = round(cache_miss_avg / cache_hit_avg, 2)
        
        # Model performance comparison
        model_stats = {}
        for profile in recent_profiles:
            model = profile.model_used
            if model not in model_stats:
                model_stats[model] = []
            model_stats[model].append(profile.total_duration_ms)
        
        analytics["model_performance"] = {}
        for model, latencies in model_stats.items():
            analytics["model_performance"][model] = {
                "request_count": len(latencies),
                "avg_latency_ms": round(statistics.mean(latencies), 2),
                "median_latency_ms": round(statistics.median(latencies), 2),
                "p95_latency_ms": round(self._percentile(latencies, 95), 2)
            }
        
        # Role-based performance
        role_stats = {}
        for profile in recent_profiles:
            role = profile.user_role
            if role not in role_stats:
                role_stats[role] = []
            role_stats[role].append(profile.total_duration_ms)
        
        analytics["role_performance"] = {}
        for role, latencies in role_stats.items():
            analytics["role_performance"][role] = {
                "request_count": len(latencies),
                "avg_latency_ms": round(statistics.mean(latencies), 2),
                "median_latency_ms": round(statistics.median(latencies), 2)
            }
        
        # Stage breakdown analysis
        analytics["stage_breakdown"] = self._analyze_stage_breakdown(recent_profiles)
        
        # Performance issues and recommendations
        analytics["performance_analysis"] = self._analyze_performance_issues(recent_profiles)
        
        return analytics
    
    def _analyze_stage_breakdown(self, profiles: List[RequestLatencyProfile]) -> Dict[str, Any]:
        """Analyze latency breakdown by pipeline stages."""
        stage_stats = {}
        
        # Collect all stage measurements
        for profile in profiles:
            for stage in profile.stages:
                if stage.duration_ms is not None:
                    stage_name = stage.stage_name
                    if stage_name not in stage_stats:
                        stage_stats[stage_name] = []
                    stage_stats[stage_name].append(stage.duration_ms)
        
        # Calculate statistics for each stage
        breakdown = {}
        for stage_name, durations in stage_stats.items():
            breakdown[stage_name] = {
                "avg_duration_ms": round(statistics.mean(durations), 2),
                "median_duration_ms": round(statistics.median(durations), 2),
                "p95_duration_ms": round(self._percentile(durations, 95), 2),
                "max_duration_ms": round(max(durations), 2),
                "sample_count": len(durations),
                "baseline_ms": self.performance_baselines.get(stage_name, 0),
                "performance_vs_baseline": "good" if statistics.mean(durations) <= self.performance_baselines.get(stage_name, float('inf')) else "slow"
            }
        
        return breakdown
    
    def _analyze_performance_issues(self, profiles: List[RequestLatencyProfile]) -> Dict[str, Any]:
        """Analyze performance issues and generate recommendations."""
        issues = []
        recommendations = []
        
        if not profiles:
            return {"issues": issues, "recommendations": recommendations}
        
        # Check overall latency
        avg_total_latency = statistics.mean([p.total_duration_ms for p in profiles])
        baseline_total = self.performance_baselines["total_request"]
        
        if avg_total_latency > baseline_total * 1.5:
            issues.append({
                "type": "high_overall_latency",
                "severity": "high",
                "description": f"Average latency ({avg_total_latency:.0f}ms) is {(avg_total_latency/baseline_total):.1f}x baseline ({baseline_total}ms)",
                "affected_requests": len(profiles)
            })
            recommendations.append({
                "type": "optimization",
                "priority": "high",
                "action": "Investigate slow pipeline stages and consider caching or model optimization"
            })
        
        # Check cache performance
        cache_hits = [p for p in profiles if p.cache_hit]
        cache_hit_rate = len(cache_hits) / len(profiles)
        
        if cache_hit_rate < 0.2:
            issues.append({
                "type": "low_cache_hit_rate",
                "severity": "medium",
                "description": f"Cache hit rate is only {cache_hit_rate:.1%}",
                "affected_requests": len(profiles) - len(cache_hits)
            })
            recommendations.append({
                "type": "caching",
                "priority": "medium",
                "action": "Review caching strategy and consider increasing cache TTL or improving cache key generation"
            })
        
        # Check for slow stages
        stage_stats = {}
        for profile in profiles:
            for stage in profile.stages:
                if stage.duration_ms is not None:
                    stage_name = stage.stage_name
                    if stage_name not in stage_stats:
                        stage_stats[stage_name] = []
                    stage_stats[stage_name].append(stage.duration_ms)
        
        for stage_name, durations in stage_stats.items():
            avg_duration = statistics.mean(durations)
            baseline = self.performance_baselines.get(stage_name, 0)
            
            if baseline > 0 and avg_duration > baseline * 2:
                issues.append({
                    "type": "slow_pipeline_stage",
                    "severity": "medium",
                    "description": f"Stage '{stage_name}' averaging {avg_duration:.0f}ms (baseline: {baseline}ms)",
                    "stage": stage_name,
                    "affected_requests": len(durations)
                })
                
                # Stage-specific recommendations
                if stage_name == "llm_processing":
                    recommendations.append({
                        "type": "model_optimization",
                        "priority": "high",
                        "action": f"Consider using faster models or optimizing prompts for {stage_name}"
                    })
                elif stage_name == "pii_redaction":
                    recommendations.append({
                        "type": "pii_optimization",
                        "priority": "medium",
                        "action": "Consider optimizing PII detection patterns or using faster entity recognition"
                    })
        
        return {
            "issues": issues,
            "recommendations": recommendations,
            "performance_score": self._calculate_performance_score(profiles)
        }
    
    def _calculate_performance_score(self, profiles: List[RequestLatencyProfile]) -> Dict[str, Any]:
        """Calculate overall performance score (0-100)."""
        if not profiles:
            return {"score": 0, "grade": "N/A"}
        
        score = 100
        
        # Penalize high latency
        avg_latency = statistics.mean([p.total_duration_ms for p in profiles])
        baseline_latency = self.performance_baselines["total_request"]
        
        if avg_latency > baseline_latency:
            latency_penalty = min(50, (avg_latency - baseline_latency) / baseline_latency * 30)
            score -= latency_penalty
        
        # Reward good cache performance
        cache_hit_rate = len([p for p in profiles if p.cache_hit]) / len(profiles)
        cache_bonus = cache_hit_rate * 10
        score += cache_bonus
        
        # Penalize high variability
        latencies = [p.total_duration_ms for p in profiles]
        if len(latencies) > 1:
            cv = statistics.stdev(latencies) / statistics.mean(latencies)  # Coefficient of variation
            if cv > 0.5:  # High variability
                variability_penalty = min(20, cv * 20)
                score -= variability_penalty
        
        score = max(0, min(100, score))
        
        # Assign grade
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        elif score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "score": round(score, 1),
            "grade": grade,
            "factors": {
                "avg_latency_ms": round(avg_latency, 2),
                "cache_hit_rate": round(cache_hit_rate, 3),
                "latency_variability": round(statistics.stdev(latencies) / statistics.mean(latencies), 3) if len(latencies) > 1 else 0
            }
        }
    
    def get_slowest_requests(self, limit: int = 10, period_hours: int = 24) -> List[Dict[str, Any]]:
        """Get the slowest requests for analysis."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=period_hours)
        recent_profiles = [
            p for p in self.request_profiles 
            if p.timestamp >= cutoff_time
        ]
        
        # Sort by total duration (descending)
        slowest = sorted(recent_profiles, key=lambda p: p.total_duration_ms, reverse=True)[:limit]
        
        result = []
        for profile in slowest:
            breakdown = profile.get_breakdown_percentages()
            result.append({
                "request_id": profile.request_id,
                "total_duration_ms": profile.total_duration_ms,
                "user_role": profile.user_role,
                "model_used": profile.model_used,
                "cache_hit": profile.cache_hit,
                "timestamp": profile.timestamp.isoformat(),
                "stage_breakdown": breakdown,
                "slowest_stage": max(breakdown.items(), key=lambda x: x[1]) if breakdown else None
            })
        
        return result
    
    def get_latency_trends(self, period_hours: int = 24, bucket_minutes: int = 60) -> Dict[str, Any]:
        """Get latency trends over time."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=period_hours)
        recent_profiles = [
            p for p in self.request_profiles 
            if p.timestamp >= cutoff_time
        ]
        
        if not recent_profiles:
            return {"buckets": [], "message": "No data available"}
        
        # Create time buckets
        bucket_size = timedelta(minutes=bucket_minutes)
        start_time = min(p.timestamp for p in recent_profiles)
        end_time = max(p.timestamp for p in recent_profiles)
        
        buckets = []
        current_time = start_time
        
        while current_time <= end_time:
            bucket_end = current_time + bucket_size
            bucket_profiles = [
                p for p in recent_profiles 
                if current_time <= p.timestamp < bucket_end
            ]
            
            if bucket_profiles:
                latencies = [p.total_duration_ms for p in bucket_profiles]
                cache_hits = len([p for p in bucket_profiles if p.cache_hit])
                
                buckets.append({
                    "timestamp": current_time.isoformat(),
                    "request_count": len(bucket_profiles),
                    "avg_latency_ms": round(statistics.mean(latencies), 2),
                    "median_latency_ms": round(statistics.median(latencies), 2),
                    "p95_latency_ms": round(self._percentile(latencies, 95), 2),
                    "cache_hit_rate": cache_hits / len(bucket_profiles)
                })
            
            current_time = bucket_end
        
        return {
            "period_hours": period_hours,
            "bucket_minutes": bucket_minutes,
            "buckets": buckets,
            "total_requests": len(recent_profiles)
        }
    
    def compare_providers(self, period_hours: int = 24) -> Dict[str, Any]:
        """Compare latency performance across different providers/models."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=period_hours)
        recent_profiles = [
            p for p in self.request_profiles 
            if p.timestamp >= cutoff_time
        ]
        
        if not recent_profiles:
            return {"message": "No data available for comparison"}
        
        # Group by model
        model_groups = {}
        for profile in recent_profiles:
            model = profile.model_used
            if model not in model_groups:
                model_groups[model] = []
            model_groups[model].append(profile)
        
        comparison = {}
        for model, profiles in model_groups.items():
            latencies = [p.total_duration_ms for p in profiles]
            cache_hits = [p for p in profiles if p.cache_hit]
            cache_misses = [p for p in profiles if not p.cache_hit]
            
            # Calculate stage averages and variability
            stage_stats = {}
            for profile in profiles:
                for stage in profile.stages:
                    if stage.duration_ms is not None:
                        stage_name = stage.stage_name
                        if stage_name not in stage_stats:
                            stage_stats[stage_name] = []
                        stage_stats[stage_name].append(stage.duration_ms)
            
            stage_analysis = {}
            for stage_name, durations in stage_stats.items():
                stage_analysis[stage_name] = {
                    "avg_ms": round(statistics.mean(durations), 2),
                    "median_ms": round(statistics.median(durations), 2),
                    "p95_ms": round(self._percentile(durations, 95), 2),
                    "std_dev_ms": round(statistics.stdev(durations), 2) if len(durations) > 1 else 0,
                    "sample_count": len(durations)
                }
            
            # Calculate cost efficiency (if available)
            total_cost = sum(getattr(p, 'metadata', {}).get('cost', 0) for p in profiles)
            cost_per_request = total_cost / len(profiles) if profiles else 0
            
            # Performance scoring
            baseline_latency = self.model_baselines.get(model, {}).get("total_request", 2500)
            avg_latency = statistics.mean(latencies)
            performance_score = max(0, 100 - ((avg_latency - baseline_latency) / baseline_latency * 50))
            
            comparison[model] = {
                "request_count": len(profiles),
                "latency_stats": {
                    "avg_latency_ms": round(avg_latency, 2),
                    "median_latency_ms": round(statistics.median(latencies), 2),
                    "p95_latency_ms": round(self._percentile(latencies, 95), 2),
                    "p99_latency_ms": round(self._percentile(latencies, 99), 2),
                    "min_latency_ms": round(min(latencies), 2),
                    "max_latency_ms": round(max(latencies), 2),
                    "std_dev_ms": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0
                },
                "cache_performance": {
                    "cache_hit_rate": len(cache_hits) / len(profiles),
                    "avg_cache_hit_latency_ms": round(statistics.mean([p.total_duration_ms for p in cache_hits]), 2) if cache_hits else 0,
                    "avg_cache_miss_latency_ms": round(statistics.mean([p.total_duration_ms for p in cache_misses]), 2) if cache_misses else 0,
                    "cache_speedup_factor": round(statistics.mean([p.total_duration_ms for p in cache_misses]) / statistics.mean([p.total_duration_ms for p in cache_hits]), 2) if cache_hits and cache_misses else 1.0
                },
                "stage_breakdown": stage_analysis,
                "cost_analysis": {
                    "total_cost_usd": round(total_cost, 4),
                    "avg_cost_per_request": round(cost_per_request, 4),
                    "cost_efficiency_score": round((1 / cost_per_request) * 1000, 2) if cost_per_request > 0 else 0  # Requests per dollar * 1000
                },
                "performance_metrics": {
                    "baseline_ms": baseline_latency,
                    "performance_vs_baseline": "excellent" if avg_latency <= baseline_latency * 0.8 else "good" if avg_latency <= baseline_latency else "needs_improvement",
                    "performance_score": round(performance_score, 1),
                    "reliability_score": round(100 - (statistics.stdev(latencies) / statistics.mean(latencies) * 100), 1) if len(latencies) > 1 else 100
                },
                "optimization_recommendations": self._generate_model_recommendations(model, profiles, stage_analysis)
            }
        
        # Generate comparative analysis
        if len(comparison) > 1:
            # Find best performers in different categories
            fastest_model = min(comparison.keys(), key=lambda m: comparison[m]["latency_stats"]["avg_latency_ms"])
            most_reliable = max(comparison.keys(), key=lambda m: comparison[m]["performance_metrics"]["reliability_score"])
            most_cost_efficient = max(comparison.keys(), key=lambda m: comparison[m]["cost_analysis"]["cost_efficiency_score"])
            
            # Calculate relative performance
            fastest_latency = comparison[fastest_model]["latency_stats"]["avg_latency_ms"]
            
            for model in comparison:
                model_latency = comparison[model]["latency_stats"]["avg_latency_ms"]
                comparison[model]["relative_performance"] = {
                    "speed_vs_fastest": round(model_latency / fastest_latency, 2),
                    "slower_by_ms": round(model_latency - fastest_latency, 2),
                    "slower_by_percent": round(((model_latency - fastest_latency) / fastest_latency) * 100, 1)
                }
            
            comparison["summary"] = {
                "fastest_model": fastest_model,
                "most_reliable_model": most_reliable,
                "most_cost_efficient_model": most_cost_efficient,
                "total_models_compared": len(comparison) - 1,  # Exclude summary itself
                "recommendation": self._generate_overall_recommendation(comparison)
            }
        
        return comparison
    
    def _generate_model_recommendations(self, model: str, profiles: List[RequestLatencyProfile], stage_analysis: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations for a specific model."""
        recommendations = []
        
        # Check for slow stages
        for stage_name, stats in stage_analysis.items():
            baseline = self.performance_baselines.get(stage_name, 0)
            if baseline > 0 and stats["avg_ms"] > baseline * 1.5:
                if stage_name == "llm_processing":
                    recommendations.append(f"Consider prompt optimization or using a faster model variant for {stage_name}")
                elif stage_name == "pii_redaction":
                    recommendations.append(f"PII redaction is slow - consider optimizing entity patterns or using faster NLP models")
                elif stage_name == "guardrails_validation":
                    recommendations.append(f"Guardrails validation is slow - review rule complexity and consider caching")
                else:
                    recommendations.append(f"Optimize {stage_name} stage - currently {stats['avg_ms']:.0f}ms vs {baseline}ms baseline")
        
        # Check cache performance
        cache_hit_rate = sum(1 for p in profiles if p.cache_hit) / len(profiles)
        if cache_hit_rate < 0.3:
            recommendations.append("Low cache hit rate - consider increasing cache TTL or improving cache key strategy")
        
        # Check variability
        latencies = [p.total_duration_ms for p in profiles]
        if len(latencies) > 1:
            cv = statistics.stdev(latencies) / statistics.mean(latencies)
            if cv > 0.3:
                recommendations.append("High latency variability detected - investigate inconsistent performance causes")
        
        return recommendations
    
    def _generate_overall_recommendation(self, comparison: Dict[str, Any]) -> str:
        """Generate an overall recommendation based on model comparison."""
        models = [k for k in comparison.keys() if k != "summary"]
        
        if not models:
            return "No models to compare"
        
        fastest = comparison["summary"]["fastest_model"]
        most_reliable = comparison["summary"]["most_reliable_model"]
        most_cost_efficient = comparison["summary"]["most_cost_efficient_model"]
        
        if fastest == most_reliable == most_cost_efficient:
            return f"Use {fastest} - it's the best performer across all metrics"
        elif fastest == most_reliable:
            return f"Use {fastest} for best speed and reliability, or {most_cost_efficient} for cost optimization"
        elif fastest == most_cost_efficient:
            return f"Use {fastest} for optimal speed and cost efficiency"
        else:
            return f"Consider {fastest} for speed, {most_reliable} for reliability, or {most_cost_efficient} for cost efficiency based on your priorities"
    
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight
    
    def clear_history(self):
        """Clear latency tracking history."""
        entries_cleared = len(self.request_profiles)
        self.request_profiles.clear()
        self.active_measurements.clear()
        
        logger.info(f"Latency history cleared: {entries_cleared} profiles removed")
        
        return {
            "profiles_cleared": entries_cleared,
            "message": f"Successfully cleared {entries_cleared} latency profiles"
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the latency tracker."""
        return {
            "status": "healthy",
            "tracked_profiles": len(self.request_profiles),
            "active_measurements": len(self.active_measurements),
            "max_history": self.max_history,
            "memory_usage_estimate": len(self.request_profiles) * 2048  # Rough estimate in bytes
        }