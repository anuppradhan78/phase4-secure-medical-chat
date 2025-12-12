"""
Helicone client wrapper for cost tracking and optimization.

This module provides integration with Helicone proxy for:
- Cost tracking per request and user role
- Token usage monitoring
- Model-specific cost analysis
- Request optimization through caching
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from openai import OpenAI
import openai

from ..models import CostData, UserRole, ModelConfig


logger = logging.getLogger(__name__)


@dataclass
class HeliconeConfig:
    """Configuration for Helicone integration."""
    api_key: str
    base_url: str = "https://oai.hconeai.com/v1"
    enable_caching: bool = True
    cache_ttl_seconds: int = 86400  # 24 hours
    enable_rate_limiting: bool = True
    enable_cost_tracking: bool = True


class HeliconeClient:
    """
    Helicone client wrapper for OpenAI API calls with cost tracking.
    
    This class provides:
    - Transparent proxy to OpenAI through Helicone
    - Automatic cost tracking and token usage monitoring
    - Request caching with configurable TTL
    - Model routing and optimization
    """
    
    def __init__(self, config: Optional[HeliconeConfig] = None):
        """Initialize Helicone client with configuration."""
        self.config = config or self._load_config_from_env()
        self._setup_client()
        self._cost_cache: Dict[str, CostData] = {}
        
    def _load_config_from_env(self) -> HeliconeConfig:
        """Load Helicone configuration from environment variables."""
        api_key = os.getenv("HELICONE_API_KEY")
        if not api_key:
            raise ValueError("HELICONE_API_KEY environment variable is required")
            
        return HeliconeConfig(
            api_key=api_key,
            base_url=os.getenv("HELICONE_BASE_URL", "https://oai.hconeai.com/v1"),
            enable_caching=os.getenv("HELICONE_ENABLE_CACHING", "true").lower() == "true",
            cache_ttl_seconds=int(os.getenv("HELICONE_CACHE_TTL", "86400")),
            enable_rate_limiting=os.getenv("HELICONE_ENABLE_RATE_LIMITING", "true").lower() == "true",
            enable_cost_tracking=os.getenv("HELICONE_ENABLE_COST_TRACKING", "true").lower() == "true"
        )
    
    def _setup_client(self):
        """Setup OpenAI client with Helicone proxy."""
        # Configure OpenAI client to use Helicone proxy
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=self.config.base_url,
            default_headers={
                "Helicone-Auth": f"Bearer {self.config.api_key}",
                "Helicone-Cache-Enabled": str(self.config.enable_caching).lower(),
                "Helicone-Cache-TTL": str(self.config.cache_ttl_seconds),
            }
        )
        
        logger.info("Helicone client configured successfully")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model_config: ModelConfig,
        user_role: UserRole,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a chat completion with cost tracking.
        
        Args:
            messages: List of chat messages
            model_config: Model configuration
            user_role: User role for cost attribution
            session_id: Optional session ID
            user_id: Optional user ID
            **kwargs: Additional OpenAI parameters
            
        Returns:
            Dict containing response and cost data
        """
        start_time = datetime.now(timezone.utc)
        
        # Prepare Helicone headers for this request
        extra_headers = {
            "Helicone-Property-Role": user_role.value,
            "Helicone-Property-Model": model_config.model,
        }
        
        if session_id:
            extra_headers["Helicone-Property-Session"] = session_id
        if user_id:
            extra_headers["Helicone-Property-User"] = user_id
        
        try:
            # Make the API call through Helicone
            response = self.client.chat.completions.create(
                model=model_config.model,
                messages=messages,
                max_tokens=model_config.max_tokens,
                temperature=model_config.temperature,
                extra_headers=extra_headers,
                **kwargs
            )
            
            end_time = datetime.now(timezone.utc)
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Extract usage and cost information
            usage = response.usage
            cost_data = self._calculate_cost(
                model=model_config.model,
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                user_role=user_role,
                session_id=session_id
            )
            
            # Check if response was served from cache (from response headers if available)
            # Note: Cache detection would need to be implemented based on Helicone's response format
            cache_hit = False  # Default to False, would be set based on Helicone headers
            cost_data.cache_hit = cache_hit
            
            # Store cost data for aggregation
            self._store_cost_data(cost_data)
            
            return {
                "response": response,
                "cost_data": cost_data,
                "latency_ms": latency_ms,
                "cache_hit": cache_hit,
                "usage": usage
            }
            
        except Exception as e:
            logger.error(f"Error in Helicone chat completion: {str(e)}")
            raise
    
    def _calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        user_role: UserRole,
        session_id: Optional[str] = None
    ) -> CostData:
        """
        Calculate cost for a request based on model and token usage.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            user_role: User role
            session_id: Optional session ID
            
        Returns:
            CostData object with cost information
        """
        # Model pricing (per 1K tokens) - as of 2024
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
        }
        
        model_pricing = pricing.get(model, pricing["gpt-3.5-turbo"])
        
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        total_cost = input_cost + output_cost
        
        return CostData(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=total_cost,
            user_role=user_role,
            session_id=session_id,
            timestamp=datetime.now(timezone.utc)
        )
    
    def _store_cost_data(self, cost_data: CostData):
        """Store cost data for aggregation and reporting."""
        key = f"{cost_data.timestamp.isoformat()}_{cost_data.session_id or 'no_session'}"
        self._cost_cache[key] = cost_data
        
        # Log cost data for monitoring
        logger.info(
            f"Cost tracking: {cost_data.model} - "
            f"${cost_data.cost_usd:.4f} - "
            f"{cost_data.total_tokens} tokens - "
            f"Role: {cost_data.user_role.value}"
        )
    
    def get_cost_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_role: Optional[UserRole] = None
    ) -> Dict[str, Any]:
        """
        Get cost summary for a given time period and/or user role.
        
        Args:
            start_date: Start date for filtering (default: beginning of today)
            end_date: End date for filtering (default: now)
            user_role: Optional user role filter
            
        Returns:
            Dict with cost summary information
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        
        # Filter cost data
        filtered_costs = []
        for cost_data in self._cost_cache.values():
            if start_date <= cost_data.timestamp <= end_date:
                if user_role is None or cost_data.user_role == user_role:
                    filtered_costs.append(cost_data)
        
        if not filtered_costs:
            return {
                "total_cost_usd": 0.0,
                "total_requests": 0,
                "total_tokens": 0,
                "cache_hit_rate": 0.0,
                "cost_by_model": {},
                "cost_by_role": {},
                "avg_cost_per_request": 0.0
            }
        
        # Calculate aggregations
        total_cost = sum(cost.cost_usd for cost in filtered_costs)
        total_requests = len(filtered_costs)
        total_tokens = sum(cost.total_tokens for cost in filtered_costs)
        cache_hits = sum(1 for cost in filtered_costs if cost.cache_hit)
        cache_hit_rate = cache_hits / total_requests if total_requests > 0 else 0.0
        
        # Cost by model
        cost_by_model = {}
        for cost in filtered_costs:
            if cost.model not in cost_by_model:
                cost_by_model[cost.model] = 0.0
            cost_by_model[cost.model] += cost.cost_usd
        
        # Cost by role
        cost_by_role = {}
        for cost in filtered_costs:
            role = cost.user_role.value
            if role not in cost_by_role:
                cost_by_role[role] = 0.0
            cost_by_role[role] += cost.cost_usd
        
        return {
            "total_cost_usd": total_cost,
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "cache_hit_rate": cache_hit_rate,
            "cost_by_model": cost_by_model,
            "cost_by_role": cost_by_role,
            "avg_cost_per_request": total_cost / total_requests if total_requests > 0 else 0.0,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
    
    def get_expensive_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most expensive queries for optimization analysis.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of expensive queries with cost and metadata
        """
        # Sort by cost descending
        sorted_costs = sorted(
            self._cost_cache.values(),
            key=lambda x: x.cost_usd,
            reverse=True
        )
        
        expensive_queries = []
        for cost_data in sorted_costs[:limit]:
            expensive_queries.append({
                "timestamp": cost_data.timestamp.isoformat(),
                "model": cost_data.model,
                "cost_usd": cost_data.cost_usd,
                "total_tokens": cost_data.total_tokens,
                "input_tokens": cost_data.input_tokens,
                "output_tokens": cost_data.output_tokens,
                "user_role": cost_data.user_role.value,
                "session_id": cost_data.session_id,
                "cache_hit": cost_data.cache_hit
            })
        
        return expensive_queries
    
    def clear_cost_cache(self):
        """Clear the cost cache (useful for testing or periodic cleanup)."""
        self._cost_cache.clear()
        logger.info("Cost cache cleared")
    
    def export_cost_data(self, filepath: str):
        """
        Export cost data to JSON file for analysis.
        
        Args:
            filepath: Path to save the cost data
        """
        cost_data_list = []
        for cost_data in self._cost_cache.values():
            cost_data_list.append({
                "timestamp": cost_data.timestamp.isoformat(),
                "model": cost_data.model,
                "input_tokens": cost_data.input_tokens,
                "output_tokens": cost_data.output_tokens,
                "total_tokens": cost_data.total_tokens,
                "cost_usd": cost_data.cost_usd,
                "user_role": cost_data.user_role.value,
                "session_id": cost_data.session_id,
                "cache_hit": cost_data.cache_hit
            })
        
        with open(filepath, 'w') as f:
            json.dump(cost_data_list, f, indent=2)
        
        logger.info(f"Cost data exported to {filepath}")


class ModelRouter:
    """
    Model router for intelligent model selection based on query complexity and user role.
    """
    
    def __init__(self):
        """Initialize model router with default configurations."""
        self.model_configs = {
            "gpt-3.5-turbo": ModelConfig(
                model="gpt-3.5-turbo",
                max_tokens=1000,
                temperature=0.7,
                provider="openai"
            ),
            "gpt-4": ModelConfig(
                model="gpt-4",
                max_tokens=2000,
                temperature=0.7,
                provider="openai"
            )
        }
        
        # Role-based model preferences
        self.role_preferences = {
            UserRole.PATIENT: ["gpt-3.5-turbo"],
            UserRole.PHYSICIAN: ["gpt-3.5-turbo", "gpt-4"],
            UserRole.ADMIN: ["gpt-3.5-turbo", "gpt-4"]
        }
    
    def select_model(
        self,
        message: str,
        user_role: UserRole,
        complexity_threshold: float = 0.5
    ) -> ModelConfig:
        """
        Select appropriate model based on query complexity and user role.
        
        Args:
            message: User message to analyze
            user_role: User role
            complexity_threshold: Threshold for using advanced model
            
        Returns:
            ModelConfig for the selected model
        """
        complexity_score = self._analyze_complexity(message)
        available_models = self.role_preferences.get(user_role, ["gpt-3.5-turbo"])
        
        # For patients, always use gpt-3.5-turbo
        if user_role == UserRole.PATIENT:
            return self.model_configs["gpt-3.5-turbo"]
        
        # For physicians and admins, use complexity-based routing
        if complexity_score >= complexity_threshold and "gpt-4" in available_models:
            return self.model_configs["gpt-4"]
        else:
            return self.model_configs["gpt-3.5-turbo"]
    
    def _analyze_complexity(self, message: str) -> float:
        """
        Analyze query complexity to determine appropriate model.
        
        Args:
            message: User message
            
        Returns:
            Complexity score from 0.0 to 1.0
        """
        # Simple complexity analysis based on message characteristics
        complexity_indicators = [
            len(message) > 500,  # Long messages
            "diagnosis" in message.lower(),  # Medical diagnosis requests
            "treatment" in message.lower(),  # Treatment planning
            "differential" in message.lower(),  # Differential diagnosis
            "research" in message.lower(),  # Research queries
            message.count("?") > 2,  # Multiple questions
            len(message.split()) > 100,  # Word count
        ]
        
        # Calculate complexity score
        complexity_score = sum(complexity_indicators) / len(complexity_indicators)
        
        # Add bonus for medical terminology
        medical_terms = [
            "symptom", "patient", "clinical", "medical", "therapy",
            "medication", "prescription", "dosage", "side effect"
        ]
        medical_term_count = sum(1 for term in medical_terms if term in message.lower())
        medical_bonus = min(medical_term_count * 0.1, 0.3)
        
        return min(complexity_score + medical_bonus, 1.0)