"""
Mock PII redaction service for testing when Presidio is not available.
"""

import logging
import uuid
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta

from ..models import RedactionResult, EntityType


class MockPIIRedactionService:
    """Mock PII redaction service for testing."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._entity_mappings: Dict[str, Dict[str, str]] = {}
        self._placeholder_counters: Dict[str, Dict[str, int]] = {}
        
        # Simple patterns for mock detection
        self.mock_patterns = {
            "PERSON": ["john", "jane", "smith", "doe"],
            "PHONE_NUMBER": ["555-", "123-", "phone"],
            "EMAIL_ADDRESS": ["@", "email"],
            "DATE_TIME": ["yesterday", "today", "tomorrow"]
        }
        
        self.logger.info("Mock PII Redaction Service initialized")
    
    def _generate_placeholder(self, entity_type: str, user_id: str) -> str:
        """Generate a typed placeholder for an entity."""
        if user_id not in self._placeholder_counters:
            self._placeholder_counters[user_id] = {}
        
        if entity_type not in self._placeholder_counters[user_id]:
            self._placeholder_counters[user_id][entity_type] = 0
        
        self._placeholder_counters[user_id][entity_type] += 1
        counter = self._placeholder_counters[user_id][entity_type]
        
        return f"[{entity_type}_{counter}]"
    
    def redact_message(self, message: str, user_id: str, 
                      session_id: Optional[str] = None) -> RedactionResult:
        """Mock redaction of PII/PHI from a message."""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        redacted_text = message
        entity_mappings = {}
        entity_types = []
        confidence_scores = {}
        entities_found = 0
        
        # Simple mock detection
        message_lower = message.lower()
        
        for entity_type, patterns in self.mock_patterns.items():
            for pattern in patterns:
                if pattern in message_lower:
                    placeholder = self._generate_placeholder(entity_type, user_id)
                    
                    # Store mapping
                    mapping_key = f"{user_id}:{session_id}"
                    if mapping_key not in self._entity_mappings:
                        self._entity_mappings[mapping_key] = {}
                    
                    self._entity_mappings[mapping_key][placeholder] = pattern
                    entity_mappings[placeholder] = pattern
                    entity_types.append(EntityType(entity_type))
                    confidence_scores[placeholder] = 0.8
                    entities_found += 1
                    
                    # Replace in text (simple replacement)
                    redacted_text = redacted_text.replace(pattern, placeholder)
                    break
        
        return RedactionResult(
            redacted_text=redacted_text,
            entities_found=entities_found,
            entity_types=entity_types,
            entity_mappings=entity_mappings,
            confidence_scores=confidence_scores
        )
    
    def de_anonymize_response(self, response: str, user_id: str, 
                            session_id: str) -> str:
        """Mock de-anonymization of response."""
        mapping_key = f"{user_id}:{session_id}"
        
        if mapping_key not in self._entity_mappings:
            return response
        
        de_anonymized_response = response
        mappings = self._entity_mappings[mapping_key]
        
        for placeholder, original_value in mappings.items():
            de_anonymized_response = de_anonymized_response.replace(
                placeholder, original_value
            )
        
        return de_anonymized_response
    
    def get_redaction_stats(self, user_id: Optional[str] = None) -> Dict:
        """Get mock redaction statistics."""
        return {
            "total_entity_mappings": len(self._entity_mappings),
            "active_sessions": len(self._entity_mappings),
            "supported_entities": list(self.mock_patterns.keys()),
            "mapping_expiry_hours": 24,
            "mock_service": True
        }
    
    def clear_user_mappings(self, user_id: str):
        """Clear mappings for a user."""
        keys_to_remove = [
            key for key in self._entity_mappings.keys()
            if key.startswith(f"{user_id}:")
        ]
        
        for key in keys_to_remove:
            if key in self._entity_mappings:
                del self._entity_mappings[key]
        
        if user_id in self._placeholder_counters:
            del self._placeholder_counters[user_id]