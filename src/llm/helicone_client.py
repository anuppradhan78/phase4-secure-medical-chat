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
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from openai import OpenAI
import openai

try:
    from ..models import CostData, UserRole, ModelConfig
except ImportError:
    # Handle case when running as script or in tests
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from models import CostData, UserRole, ModelConfig


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
        """Setup OpenAI client with or without Helicone proxy."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # Check if using Helicone proxy
        if self.config.base_url == "https://api.openai.com/v1":
            # Direct OpenAI API (no Helicone)
            self.client = OpenAI(api_key=openai_api_key)
            logger.info("OpenAI client configured for direct API access")
        else:
            # Configure OpenAI client to use Helicone proxy
            self.client = OpenAI(
                api_key=openai_api_key,
                base_url=self.config.base_url,
                default_headers={
                    "Helicone-Auth": f"Bearer {self.config.api_key}",
                    "Helicone-Cache-Enabled": str(self.config.enable_caching).lower(),
                    "Helicone-Cache-TTL": str(self.config.cache_ttl_seconds),
                }
            )
            logger.info("OpenAI client configured with Helicone proxy")
        
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


class QueryComplexityAnalyzer:
    """
    Advanced query complexity analyzer for intelligent model routing.
    
    This analyzer evaluates multiple dimensions of query complexity:
    - Linguistic complexity (sentence structure, vocabulary)
    - Medical complexity (terminology, clinical reasoning)
    - Task complexity (diagnosis, treatment planning, research)
    - Context complexity (multi-step reasoning, differential diagnosis)
    """
    
    def __init__(self):
        """Initialize complexity analyzer with medical knowledge base."""
        # Medical terminology categories for complexity scoring
        self.medical_terms = {
            "basic": [
                "symptom", "pain", "fever", "headache", "cough", "cold", "flu",
                "medication", "doctor", "hospital", "clinic", "appointment"
            ],
            "intermediate": [
                "diagnosis", "treatment", "therapy", "prescription", "dosage",
                "side effect", "allergy", "chronic", "acute", "infection",
                "inflammation", "blood pressure", "diabetes", "asthma"
            ],
            "advanced": [
                "differential diagnosis", "pathophysiology", "pharmacokinetics",
                "contraindication", "comorbidity", "prognosis", "etiology",
                "epidemiology", "biomarker", "immunosuppression", "nephrotoxicity",
                "hepatotoxicity", "cardiotoxicity", "oncology", "hematology"
            ],
            "expert": [
                "pharmacogenomics", "proteomics", "metabolomics", "epigenetics",
                "immunohistochemistry", "cytogenetics", "molecular diagnostics",
                "precision medicine", "personalized therapy", "biomarker stratification"
            ]
        }
        
        # Clinical reasoning indicators
        self.reasoning_indicators = [
            "differential", "rule out", "consider", "likely", "unlikely",
            "probable", "possible", "exclude", "include", "workup",
            "investigate", "monitor", "follow up", "reassess", "evaluate"
        ]
        
        # Complex task indicators
        self.complex_tasks = [
            "treatment plan", "management strategy", "diagnostic workup",
            "risk assessment", "prognosis", "clinical decision",
            "therapeutic approach", "monitoring plan", "follow-up strategy"
        ]
    
    def analyze_complexity(self, message: str) -> Dict[str, Any]:
        """
        Comprehensive complexity analysis of a medical query.
        
        Args:
            message: User message to analyze
            
        Returns:
            Dict with detailed complexity analysis
        """
        message_lower = message.lower()
        words = message.split()
        
        # 1. Linguistic complexity
        linguistic_score = self._analyze_linguistic_complexity(message, words)
        
        # 2. Medical terminology complexity
        medical_score = self._analyze_medical_complexity(message_lower)
        
        # 3. Clinical reasoning complexity
        reasoning_score = self._analyze_reasoning_complexity(message_lower)
        
        # 4. Task complexity
        task_score = self._analyze_task_complexity(message_lower)
        
        # 5. Context and length complexity
        context_score = self._analyze_context_complexity(message, words)
        
        # Calculate weighted overall complexity
        weights = {
            "linguistic": 0.15,
            "medical": 0.25,
            "reasoning": 0.25,
            "task": 0.20,
            "context": 0.15
        }
        
        overall_score = (
            linguistic_score * weights["linguistic"] +
            medical_score * weights["medical"] +
            reasoning_score * weights["reasoning"] +
            task_score * weights["task"] +
            context_score * weights["context"]
        )
        
        return {
            "overall_score": min(overall_score, 1.0),
            "components": {
                "linguistic": linguistic_score,
                "medical": medical_score,
                "reasoning": reasoning_score,
                "task": task_score,
                "context": context_score
            },
            "indicators": {
                "word_count": len(words),
                "sentence_count": message.count('.') + message.count('!') + message.count('?'),
                "question_count": message.count('?'),
                "medical_terms_found": self._count_medical_terms(message_lower),
                "reasoning_indicators": self._count_reasoning_indicators(message_lower),
                "complex_tasks": self._count_complex_tasks(message_lower)
            },
            "recommendation": self._get_model_recommendation(overall_score)
        }
    
    def _analyze_linguistic_complexity(self, message: str, words: List[str]) -> float:
        """Analyze linguistic complexity based on structure and vocabulary."""
        score = 0.0
        
        # Length indicators
        if len(words) > 100:
            score += 0.3
        elif len(words) > 50:
            score += 0.2
        elif len(words) > 20:
            score += 0.1
        
        # Sentence complexity
        sentence_count = max(1, message.count('.') + message.count('!') + message.count('?'))
        avg_sentence_length = len(words) / sentence_count
        if avg_sentence_length > 25:
            score += 0.2
        elif avg_sentence_length > 15:
            score += 0.1
        
        # Question complexity
        question_count = message.count('?')
        if question_count > 3:
            score += 0.2
        elif question_count > 1:
            score += 0.1
        
        # Complex punctuation and structure
        if any(punct in message for punct in [';', ':', '(', ')', '[', ']']):
            score += 0.1
        
        return min(score, 1.0)
    
    def _analyze_medical_complexity(self, message_lower: str) -> float:
        """Analyze medical terminology complexity."""
        score = 0.0
        
        # Count terms by complexity level
        basic_count = sum(1 for term in self.medical_terms["basic"] if term in message_lower)
        intermediate_count = sum(1 for term in self.medical_terms["intermediate"] if term in message_lower)
        advanced_count = sum(1 for term in self.medical_terms["advanced"] if term in message_lower)
        expert_count = sum(1 for term in self.medical_terms["expert"] if term in message_lower)
        
        # Weight by complexity level
        weighted_score = (
            basic_count * 0.1 +
            intermediate_count * 0.3 +
            advanced_count * 0.6 +
            expert_count * 1.0
        )
        
        # Normalize by message length (approximate)
        word_count = len(message_lower.split())
        if word_count > 0:
            score = min(weighted_score / (word_count * 0.1), 1.0)
        
        return score
    
    def _analyze_reasoning_complexity(self, message_lower: str) -> float:
        """Analyze clinical reasoning complexity."""
        reasoning_count = sum(1 for indicator in self.reasoning_indicators 
                            if indicator in message_lower)
        
        # Normalize to 0-1 scale
        return min(reasoning_count * 0.2, 1.0)
    
    def _analyze_task_complexity(self, message_lower: str) -> float:
        """Analyze task complexity."""
        task_count = sum(1 for task in self.complex_tasks 
                        if task in message_lower)
        
        # Normalize to 0-1 scale
        return min(task_count * 0.3, 1.0)
    
    def _analyze_context_complexity(self, message: str, words: List[str]) -> float:
        """Analyze context and structural complexity."""
        score = 0.0
        
        # Multi-part questions or requests
        if message.count('?') > 1:
            score += 0.2
        
        # Lists or enumerations
        if any(marker in message for marker in ['1.', '2.', '3.', 'a)', 'b)', 'c)', '-', '*']):
            score += 0.2
        
        # Conditional statements
        if any(cond in message.lower() for cond in ['if', 'when', 'unless', 'provided that']):
            score += 0.1
        
        # Comparative statements
        if any(comp in message.lower() for comp in ['versus', 'vs', 'compared to', 'rather than']):
            score += 0.1
        
        # Time-based complexity
        if any(time in message.lower() for time in ['history', 'timeline', 'progression', 'course']):
            score += 0.1
        
        return min(score, 1.0)
    
    def _count_medical_terms(self, message_lower: str) -> Dict[str, int]:
        """Count medical terms by category."""
        return {
            category: sum(1 for term in terms if term in message_lower)
            for category, terms in self.medical_terms.items()
        }
    
    def _count_reasoning_indicators(self, message_lower: str) -> int:
        """Count clinical reasoning indicators."""
        return sum(1 for indicator in self.reasoning_indicators 
                  if indicator in message_lower)
    
    def _count_complex_tasks(self, message_lower: str) -> int:
        """Count complex task indicators."""
        return sum(1 for task in self.complex_tasks 
                  if task in message_lower)
    
    def _get_model_recommendation(self, complexity_score: float) -> str:
        """Get model recommendation based on complexity score."""
        if complexity_score >= 0.7:
            return "gpt-4"  # High complexity requires advanced model
        elif complexity_score >= 0.4:
            return "gpt-4-recommended"  # Moderate complexity benefits from advanced model
        else:
            return "gpt-3.5-turbo"  # Low complexity can use efficient model


class PromptOptimizer:
    """
    Prompt optimization service to reduce token usage while maintaining quality.
    
    This service provides techniques to optimize prompts for cost efficiency:
    - Remove redundant information
    - Compress verbose descriptions
    - Use efficient prompt structures
    - Apply role-specific optimizations
    """
    
    def __init__(self):
        """Initialize prompt optimizer."""
        # Common redundant phrases to remove or compress
        self.redundant_phrases = [
            "I would like to know",
            "Could you please tell me",
            "I was wondering if",
            "Can you help me understand",
            "I need to know",
            "Please provide information about"
        ]
        
        # Compression mappings for common medical phrases
        self.compression_map = {
            "patient is experiencing": "patient has",
            "is complaining of": "reports",
            "has been diagnosed with": "diagnosed:",
            "is currently taking": "taking:",
            "has a history of": "hx:",
            "physical examination reveals": "exam:",
            "laboratory results show": "labs:",
            "imaging studies demonstrate": "imaging:",
        }
    
    def optimize_prompt(self, message: str, user_role: UserRole) -> Dict[str, Any]:
        """
        Optimize prompt for token efficiency while preserving meaning.
        
        Args:
            message: Original user message
            user_role: User role for role-specific optimizations
            
        Returns:
            Dict with optimized prompt and optimization details
        """
        original_length = len(message.split())
        optimized_message = message
        optimizations_applied = []
        
        # 1. Remove redundant phrases
        optimized_message, removed_phrases = self._remove_redundant_phrases(optimized_message)
        if removed_phrases:
            optimizations_applied.extend(removed_phrases)
        
        # 2. Apply compression mappings
        optimized_message, compressions = self._apply_compressions(optimized_message)
        if compressions:
            optimizations_applied.extend(compressions)
        
        # 3. Role-specific optimizations
        optimized_message, role_opts = self._apply_role_optimizations(optimized_message, user_role)
        if role_opts:
            optimizations_applied.extend(role_opts)
        
        # 4. Structure optimization
        optimized_message, struct_opts = self._optimize_structure(optimized_message)
        if struct_opts:
            optimizations_applied.extend(struct_opts)
        
        optimized_length = len(optimized_message.split())
        token_savings = original_length - optimized_length
        savings_percentage = (token_savings / original_length * 100) if original_length > 0 else 0
        
        return {
            "original_message": message,
            "optimized_message": optimized_message,
            "original_token_count": original_length,
            "optimized_token_count": optimized_length,
            "tokens_saved": token_savings,
            "savings_percentage": savings_percentage,
            "optimizations_applied": optimizations_applied,
            "should_use_optimized": token_savings >= 5  # Use if saves 5+ tokens
        }
    
    def _remove_redundant_phrases(self, message: str) -> Tuple[str, List[str]]:
        """Remove redundant conversational phrases."""
        optimized = message
        removed = []
        
        for phrase in self.redundant_phrases:
            if phrase.lower() in optimized.lower():
                # Remove the phrase and clean up spacing
                optimized = optimized.replace(phrase, "").replace("  ", " ").strip()
                removed.append(f"removed_phrase: {phrase}")
        
        return optimized, removed
    
    def _apply_compressions(self, message: str) -> Tuple[str, List[str]]:
        """Apply medical phrase compressions."""
        optimized = message
        applied = []
        
        for long_phrase, short_phrase in self.compression_map.items():
            if long_phrase.lower() in optimized.lower():
                optimized = optimized.replace(long_phrase, short_phrase)
                applied.append(f"compressed: {long_phrase} -> {short_phrase}")
        
        return optimized, applied
    
    def _apply_role_optimizations(self, message: str, user_role: UserRole) -> Tuple[str, List[str]]:
        """Apply role-specific optimizations."""
        optimized = message
        applied = []
        
        if user_role == UserRole.PHYSICIAN:
            # Physicians can handle more technical, compressed language
            medical_compressions = {
                "blood pressure": "BP",
                "heart rate": "HR",
                "respiratory rate": "RR",
                "temperature": "temp",
                "white blood cell": "WBC",
                "red blood cell": "RBC",
                "hemoglobin": "Hgb",
                "hematocrit": "Hct"
            }
            
            for long_term, short_term in medical_compressions.items():
                if long_term.lower() in optimized.lower():
                    optimized = optimized.replace(long_term, short_term)
                    applied.append(f"medical_abbreviation: {long_term} -> {short_term}")
        
        elif user_role == UserRole.PATIENT:
            # For patients, focus on clarity over compression
            # Remove medical jargon that might be confusing
            pass  # Keep patient messages more natural
        
        return optimized, applied
    
    def _optimize_structure(self, message: str) -> Tuple[str, List[str]]:
        """Optimize message structure for efficiency."""
        optimized = message
        applied = []
        
        # Remove excessive whitespace
        if "  " in optimized:
            optimized = " ".join(optimized.split())
            applied.append("normalized_whitespace")
        
        # Optimize question structure
        if optimized.count("?") > 1:
            # Convert multiple questions to a list format
            questions = [q.strip() + "?" for q in optimized.split("?") if q.strip()]
            if len(questions) > 1:
                optimized = "Questions: " + " ".join(f"{i+1}) {q}" for i, q in enumerate(questions))
                applied.append("structured_questions")
        
        return optimized, applied


class ModelRouter:
    """
    Enhanced model router for intelligent model selection based on query complexity and user role.
    
    This router provides:
    - Advanced complexity analysis
    - Cost-aware model selection
    - Performance optimization
    - Usage pattern learning
    """
    
    def __init__(self):
        """Initialize enhanced model router with configurations."""
        self.complexity_analyzer = QueryComplexityAnalyzer()
        self.prompt_optimizer = PromptOptimizer()
        
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
        
        # Enhanced role-based model preferences with cost considerations
        self.role_preferences = {
            UserRole.PATIENT: {
                "allowed_models": ["gpt-3.5-turbo"],
                "complexity_threshold": 0.8,  # High threshold for cost control
                "max_tokens": 800,
                "optimize_prompts": True
            },
            UserRole.PHYSICIAN: {
                "allowed_models": ["gpt-3.5-turbo", "gpt-4"],
                "complexity_threshold": 0.2,  # Lower threshold for better quality
                "max_tokens": 1500,
                "optimize_prompts": False  # Preserve clinical language
            },
            UserRole.ADMIN: {
                "allowed_models": ["gpt-3.5-turbo", "gpt-4"],
                "complexity_threshold": 0.3,  # Moderate threshold
                "max_tokens": 2000,
                "optimize_prompts": True
            }
        }
        
        # Track routing decisions for optimization
        self.routing_history = []
    
    def select_model(
        self,
        message: str,
        user_role: UserRole,
        session_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced model selection with complexity analysis and optimization.
        
        Args:
            message: User message to analyze
            user_role: User role
            session_context: Optional session context for optimization
            
        Returns:
            Dict with model config and routing details
        """
        # Get role preferences
        role_config = self.role_preferences.get(user_role, self.role_preferences[UserRole.PATIENT])
        
        # Analyze query complexity
        complexity_analysis = self.complexity_analyzer.analyze_complexity(message)
        complexity_score = complexity_analysis["overall_score"]
        
        # Optimize prompt if enabled for this role
        optimization_result = None
        optimized_message = message
        if role_config["optimize_prompts"]:
            optimization_result = self.prompt_optimizer.optimize_prompt(message, user_role)
            if optimization_result["should_use_optimized"]:
                optimized_message = optimization_result["optimized_message"]
        
        # Select model based on complexity and role
        selected_model = self._select_model_by_complexity(
            complexity_score, 
            role_config, 
            complexity_analysis["recommendation"]
        )
        
        # Create model config with role-specific settings
        model_config = ModelConfig(
            model=selected_model,
            max_tokens=role_config["max_tokens"],
            temperature=0.7,
            provider="openai"
        )
        
        # Record routing decision
        routing_decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_role": user_role.value,
            "original_message_length": len(message.split()),
            "optimized_message_length": len(optimized_message.split()) if optimization_result else None,
            "complexity_score": complexity_score,
            "complexity_components": complexity_analysis["components"],
            "selected_model": selected_model,
            "routing_reason": self._get_routing_reason(complexity_score, role_config, selected_model),
            "optimization_applied": optimization_result is not None and optimization_result["should_use_optimized"],
            "tokens_saved": optimization_result["tokens_saved"] if optimization_result else 0
        }
        
        self.routing_history.append(routing_decision)
        
        return {
            "model_config": model_config,
            "optimized_message": optimized_message,
            "complexity_analysis": complexity_analysis,
            "optimization_result": optimization_result,
            "routing_decision": routing_decision
        }
    
    def _select_model_by_complexity(
        self, 
        complexity_score: float, 
        role_config: Dict[str, Any], 
        recommendation: str
    ) -> str:
        """Select model based on complexity analysis and role configuration."""
        available_models = role_config["allowed_models"]
        threshold = role_config["complexity_threshold"]
        
        # If only one model available, use it
        if len(available_models) == 1:
            return available_models[0]
        
        # Use complexity-based selection
        if complexity_score >= threshold and "gpt-4" in available_models:
            return "gpt-4"
        elif recommendation == "gpt-4" and "gpt-4" in available_models and complexity_score >= 0.3:
            # Use GPT-4 if recommended and complexity is at least moderate
            return "gpt-4"
        else:
            return "gpt-3.5-turbo"
    
    def _get_routing_reason(self, complexity_score: float, role_config: Dict[str, Any], selected_model: str) -> str:
        """Get human-readable reason for model selection."""
        threshold = role_config["complexity_threshold"]
        
        if selected_model == "gpt-4":
            if complexity_score >= threshold:
                return f"High complexity ({complexity_score:.2f} >= {threshold}) requires advanced model"
            else:
                return f"Moderate complexity ({complexity_score:.2f}) benefits from advanced model"
        else:
            if complexity_score < threshold:
                return f"Low complexity ({complexity_score:.2f} < {threshold}) suitable for efficient model"
            else:
                return f"Role restriction: {role_config['allowed_models']}"
    
    def get_routing_analytics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get routing analytics for optimization insights.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with routing analytics
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        recent_decisions = [
            decision for decision in self.routing_history
            if datetime.fromisoformat(decision["timestamp"]) >= cutoff_date
        ]
        
        if not recent_decisions:
            return {"message": "No routing decisions in the specified period"}
        
        # Calculate analytics
        total_decisions = len(recent_decisions)
        gpt4_usage = sum(1 for d in recent_decisions if d["selected_model"] == "gpt-4")
        gpt35_usage = total_decisions - gpt4_usage
        
        # Role-based analytics
        role_breakdown = {}
        for decision in recent_decisions:
            role = decision["user_role"]
            if role not in role_breakdown:
                role_breakdown[role] = {"total": 0, "gpt-4": 0, "gpt-3.5-turbo": 0}
            role_breakdown[role]["total"] += 1
            role_breakdown[role][decision["selected_model"]] += 1
        
        # Complexity analytics
        complexity_scores = [d["complexity_score"] for d in recent_decisions]
        avg_complexity = sum(complexity_scores) / len(complexity_scores)
        
        # Optimization analytics
        optimizations_applied = sum(1 for d in recent_decisions if d["optimization_applied"])
        total_tokens_saved = sum(d["tokens_saved"] for d in recent_decisions)
        
        return {
            "period_days": days,
            "total_decisions": total_decisions,
            "model_usage": {
                "gpt-4": {"count": gpt4_usage, "percentage": gpt4_usage / total_decisions * 100},
                "gpt-3.5-turbo": {"count": gpt35_usage, "percentage": gpt35_usage / total_decisions * 100}
            },
            "role_breakdown": role_breakdown,
            "complexity_analytics": {
                "average_complexity": avg_complexity,
                "min_complexity": min(complexity_scores),
                "max_complexity": max(complexity_scores)
            },
            "optimization_analytics": {
                "optimizations_applied": optimizations_applied,
                "optimization_rate": optimizations_applied / total_decisions * 100,
                "total_tokens_saved": total_tokens_saved,
                "avg_tokens_saved_per_optimization": total_tokens_saved / max(optimizations_applied, 1)
            }
        }
    
    def get_model_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get model usage recommendations based on routing history.
        
        Returns:
            List of recommendations for optimization
        """
        recommendations = []
        
        if len(self.routing_history) < 10:
            return [{"type": "info", "message": "Insufficient data for recommendations"}]
        
        # Analyze recent routing patterns
        recent_decisions = self.routing_history[-100:]  # Last 100 decisions
        
        # Check for potential over-use of GPT-4
        gpt4_usage = sum(1 for d in recent_decisions if d["selected_model"] == "gpt-4")
        gpt4_rate = gpt4_usage / len(recent_decisions)
        
        if gpt4_rate > 0.6:  # More than 60% GPT-4 usage
            avg_complexity = sum(d["complexity_score"] for d in recent_decisions if d["selected_model"] == "gpt-4") / max(gpt4_usage, 1)
            if avg_complexity < 0.5:
                recommendations.append({
                    "type": "cost_optimization",
                    "priority": "high",
                    "message": f"High GPT-4 usage ({gpt4_rate:.1%}) with moderate complexity ({avg_complexity:.2f}). "
                              f"Consider raising complexity threshold to reduce costs.",
                    "potential_savings": "20-40% cost reduction"
                })
        
        # Check for optimization opportunities
        total_tokens_saved = sum(d["tokens_saved"] for d in recent_decisions)
        optimizations_applied = sum(1 for d in recent_decisions if d["optimization_applied"])
        
        if optimizations_applied > 0:
            avg_savings = total_tokens_saved / optimizations_applied
            recommendations.append({
                "type": "optimization_success",
                "priority": "info",
                "message": f"Prompt optimization is working well. "
                          f"Average {avg_savings:.1f} tokens saved per optimization.",
                "impact": f"Total {total_tokens_saved} tokens saved"
            })
        
        # Check for role-specific patterns
        role_patterns = {}
        for decision in recent_decisions:
            role = decision["user_role"]
            if role not in role_patterns:
                role_patterns[role] = []
            role_patterns[role].append(decision)
        
        for role, decisions in role_patterns.items():
            if len(decisions) >= 5:
                avg_complexity = sum(d["complexity_score"] for d in decisions) / len(decisions)
                gpt4_usage_role = sum(1 for d in decisions if d["selected_model"] == "gpt-4") / len(decisions)
                
                if role == "patient" and gpt4_usage_role > 0:
                    recommendations.append({
                        "type": "role_optimization",
                        "priority": "medium",
                        "message": f"Patient queries using GPT-4 ({gpt4_usage_role:.1%}). "
                                  f"Consider restricting patients to GPT-3.5 for cost control.",
                        "role": role
                    })
        
        return recommendations if recommendations else [{"type": "info", "message": "No optimization recommendations at this time"}]