"""
Mock LLM Gateway for testing when external services are not available.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

from ..models import ChatRequest, ChatResponse, UserRole


class MockLLMGateway:
    """Mock LLM Gateway for testing."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.request_count = 0
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
            "total_cost_usd": self.request_count * 0.002,
            "queries_today": self.request_count,
            "cache_hit_rate": 0.0,
            "avg_latency_ms": 150.0,
            "cost_by_model": {"mock-gpt-3.5-turbo": self.request_count * 0.002},
            "cost_by_role": {
                "patient": self.request_count * 0.001,
                "physician": self.request_count * 0.001
            },
            "security_events_today": 0,
            "mock_service": True
        }