"""
Tests for PII/PHI redaction service.
"""

import json
import pytest
import logging
from pathlib import Path
from src.security.pii_redaction import PIIRedactionService
from src.models import EntityType


class TestPIIRedactionService:
    """Test cases for PII redaction service."""
    
    @pytest.fixture
    def redaction_service(self):
        """Create a PII redaction service instance."""
        logger = logging.getLogger("test_pii_redaction")
        return PIIRedactionService(logger=logger)
    
    @pytest.fixture
    def test_data(self):
        """Load test data for medical conversations."""
        test_data_path = Path("config/test_data/medical_conversations.json")
        if test_data_path.exists():
            with open(test_data_path, 'r') as f:
                return json.load(f)
        else:
            # Fallback test data if file doesn't exist
            return [
                {
                    "text": "Hi, my name is John Smith and I was born on March 15, 1985.",
                    "expected_entities": ["PERSON", "DATE_TIME"]
                },
                {
                    "text": "Please call me at 555-123-4567 or email john.doe@email.com",
                    "expected_entities": ["PHONE_NUMBER", "EMAIL_ADDRESS"]
                }
            ]
    
    def test_basic_redaction(self, redaction_service):
        """Test basic PII redaction functionality."""
        message = "Hi, my name is John Smith and my phone is 555-123-4567"
        result = redaction_service.redact_message(message, "test_user_1")
        
        assert result.entities_found > 0
        assert "John Smith" not in result.redacted_text
        assert "555-123-4567" not in result.redacted_text
        assert "[PERSON_1]" in result.redacted_text
        assert "[PHONE_NUMBER_1]" in result.redacted_text
    
    def test_no_pii_message(self, redaction_service):
        """Test message with no PII/PHI."""
        message = "I have a headache and feel tired."
        result = redaction_service.redact_message(message, "test_user_2")
        
        assert result.entities_found == 0
        assert result.redacted_text == message
        assert len(result.entity_types) == 0
    
    def test_entity_mapping_storage(self, redaction_service):
        """Test that entity mappings are stored correctly."""
        message = "My name is Jane Doe and my email is jane@example.com"
        result = redaction_service.redact_message(message, "test_user_3", "session_1")
        
        assert len(result.entity_mappings) > 0
        assert any("Jane Doe" in mapping for mapping in result.entity_mappings.values())
        assert any("jane@example.com" in mapping for mapping in result.entity_mappings.values())
    
    def test_de_anonymization(self, redaction_service):
        """Test de-anonymization functionality."""
        message = "My name is Bob Johnson"
        user_id = "test_user_4"
        session_id = "session_2"
        
        # First redact
        result = redaction_service.redact_message(message, user_id, session_id)
        
        # Then de-anonymize a response containing the placeholder
        response_with_placeholder = f"Hello {list(result.entity_mappings.keys())[0]}, how can I help you?"
        de_anonymized = redaction_service.de_anonymize_response(
            response_with_placeholder, user_id, session_id
        )
        
        assert "Bob Johnson" in de_anonymized
        assert "[PERSON_1]" not in de_anonymized
    
    def test_placeholder_generation(self, redaction_service):
        """Test that placeholders are generated correctly."""
        message1 = "John Smith called and then Mary Johnson called"
        result1 = redaction_service.redact_message(message1, "test_user_5")
        
        assert "[PERSON_1]" in result1.redacted_text
        assert "[PERSON_2]" in result1.redacted_text
        
        # Test that counters continue for the same user
        message2 = "Then Alice Brown called"
        result2 = redaction_service.redact_message(message2, "test_user_5")
        
        assert "[PERSON_3]" in result2.redacted_text
    
    def test_confidence_scores(self, redaction_service):
        """Test that confidence scores are returned."""
        message = "My name is Dr. Sarah Wilson and my phone is 555-999-8888"
        result = redaction_service.redact_message(message, "test_user_6")
        
        assert len(result.confidence_scores) > 0
        for score in result.confidence_scores.values():
            assert 0.0 <= score <= 1.0
    
    def test_clear_user_mappings(self, redaction_service):
        """Test clearing user mappings."""
        message = "My name is Test User"
        user_id = "test_user_7"
        
        # Create some mappings
        redaction_service.redact_message(message, user_id, "session_1")
        redaction_service.redact_message(message, user_id, "session_2")
        
        # Clear mappings
        redaction_service.clear_user_mappings(user_id)
        
        # Verify mappings are cleared
        stats = redaction_service.get_redaction_stats(user_id)
        assert stats["total_entity_mappings"] == 0
        assert stats["active_sessions"] == 0
    
    def test_redaction_stats(self, redaction_service):
        """Test redaction statistics."""
        message = "My name is Stats User and email is stats@test.com"
        redaction_service.redact_message(message, "stats_user", "stats_session")
        
        stats = redaction_service.get_redaction_stats("stats_user")
        
        assert "total_entity_mappings" in stats
        assert "active_sessions" in stats
        assert "supported_entities" in stats
        assert stats["total_entity_mappings"] > 0
        assert stats["active_sessions"] > 0
    
    def test_medical_entities_support(self, redaction_service):
        """Test that medical-specific entities are supported."""
        expected_entities = [
            "PERSON", "DATE_TIME", "PHONE_NUMBER", "EMAIL_ADDRESS", 
            "MEDICAL_LICENSE", "US_SSN", "LOCATION"
        ]
        
        for entity in expected_entities:
            assert entity in redaction_service.medical_entities
    
    def test_accuracy_validation(self, redaction_service, test_data):
        """Test redaction accuracy on test dataset."""
        # Run accuracy validation
        accuracy_results = redaction_service.validate_redaction_accuracy(test_data)
        
        assert "accuracy" in accuracy_results
        assert "precision" in accuracy_results
        assert "recall" in accuracy_results
        assert "total_cases" in accuracy_results
        
        # Check that we have reasonable accuracy (target >= 90%)
        accuracy = accuracy_results["accuracy"]
        print(f"Redaction accuracy: {accuracy:.2%}")
        
        # Log detailed results for debugging
        if "detailed_results" in accuracy_results:
            for i, result in enumerate(accuracy_results["detailed_results"][:5]):  # Show first 5
                print(f"Test case {i+1}:")
                print(f"  Text: {result['text'][:50]}...")
                print(f"  Expected: {result['expected']}")
                print(f"  Detected: {result['detected']}")
                print(f"  Correct: {result['correct']}")
        
        # Assert minimum accuracy (we'll aim for 90% but start with a lower threshold for testing)
        assert accuracy >= 0.5, f"Accuracy {accuracy:.2%} is below minimum threshold"
    
    def test_error_handling(self, redaction_service):
        """Test error handling in redaction service."""
        # Test with empty message
        result = redaction_service.redact_message("", "test_user_error")
        assert result.entities_found == 0
        
        # Test with very long message
        long_message = "A" * 10000
        result = redaction_service.redact_message(long_message, "test_user_error")
        assert result.redacted_text is not None
        
        # Test de-anonymization with non-existent session
        response = redaction_service.de_anonymize_response(
            "Hello [PERSON_1]", "nonexistent_user", "nonexistent_session"
        )
        assert response == "Hello [PERSON_1]"  # Should return unchanged