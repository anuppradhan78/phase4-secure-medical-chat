#!/usr/bin/env python3
"""
Demo script for PII/PHI redaction service.
Shows the redaction service in action with medical conversations.
"""

import sys
import os
import logging
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.security.pii_redaction import PIIRedactionService


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('pii_redaction_demo.log')
        ]
    )
    return logging.getLogger(__name__)


def demo_basic_redaction(service, logger):
    """Demonstrate basic PII redaction."""
    print("\n" + "="*60)
    print("BASIC PII REDACTION DEMO")
    print("="*60)
    
    test_messages = [
        "Hi, my name is Dr. Sarah Johnson and my phone is 555-123-4567",
        "Patient John Smith was born on March 15, 1985 and lives at 123 Main St, Boston, MA",
        "Please contact me at sarah.johnson@hospital.org for the lab results",
        "My SSN is 123-45-6789 and I need to schedule an appointment for next Tuesday",
        "The patient called yesterday at 3 PM about chest pain symptoms"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}:")
        print(f"Original: {message}")
        
        result = service.redact_message(message, f"demo_user_{i}", f"session_{i}")
        
        print(f"Redacted: {result.redacted_text}")
        print(f"Entities found: {result.entities_found}")
        print(f"Entity types: {[et.value for et in result.entity_types]}")
        print(f"Confidence scores: {result.confidence_scores}")
        
        logger.info(f"Redacted message {i}: {result.entities_found} entities found")


def demo_de_anonymization(service, logger):
    """Demonstrate de-anonymization."""
    print("\n" + "="*60)
    print("DE-ANONYMIZATION DEMO")
    print("="*60)
    
    user_id = "demo_user_deano"
    session_id = "session_deano"
    
    # First, redact a message
    original_message = "Hi Dr. Smith, this is John Doe calling about my appointment on Friday"
    print(f"Original message: {original_message}")
    
    result = service.redact_message(original_message, user_id, session_id)
    print(f"Redacted message: {result.redacted_text}")
    
    # Simulate an AI response that uses the placeholders
    ai_response = f"Hello {list(result.entity_mappings.keys())[0]}, I can help you with your appointment."
    print(f"AI response with placeholders: {ai_response}")
    
    # De-anonymize the response
    final_response = service.de_anonymize_response(ai_response, user_id, session_id)
    print(f"De-anonymized response: {final_response}")
    
    logger.info("Demonstrated de-anonymization process")


def demo_accuracy_validation(service, logger):
    """Demonstrate accuracy validation on test dataset."""
    print("\n" + "="*60)
    print("ACCURACY VALIDATION DEMO")
    print("="*60)
    
    # Load test data
    test_data_path = Path("config/test_data/medical_conversations.json")
    if test_data_path.exists():
        with open(test_data_path, 'r') as f:
            test_data = json.load(f)
    else:
        # Fallback test data
        test_data = [
            {
                "text": "Hi, my name is John Smith and I was born on March 15, 1985.",
                "expected_entities": ["PERSON", "DATE_TIME"]
            },
            {
                "text": "Please call me at 555-123-4567 or email john.doe@email.com",
                "expected_entities": ["PHONE_NUMBER", "EMAIL_ADDRESS"]
            }
        ]
    
    print(f"Running accuracy validation on {len(test_data)} test cases...")
    
    results = service.validate_redaction_accuracy(test_data)
    
    print(f"Overall Accuracy: {results['accuracy']:.2%}")
    print(f"Precision: {results['precision']:.2%}")
    print(f"Recall: {results['recall']:.2%}")
    print(f"Total test cases: {results['total_cases']}")
    print(f"Correct detections: {results['correct_detections']}")
    
    # Show some detailed results
    print("\nDetailed Results (first 5 cases):")
    for i, result in enumerate(results['detailed_results'][:5]):
        print(f"  Case {i+1}: {'✓' if result['correct'] else '✗'}")
        print(f"    Expected: {result['expected']}")
        print(f"    Detected: {result['detected']}")
    
    logger.info(f"Accuracy validation completed: {results['accuracy']:.2%} accuracy")


def demo_statistics(service, logger):
    """Demonstrate redaction statistics."""
    print("\n" + "="*60)
    print("REDACTION STATISTICS DEMO")
    print("="*60)
    
    stats = service.get_redaction_stats()
    
    print("Current Redaction Statistics:")
    print(f"  Total entity mappings: {stats.get('total_entity_mappings', 0)}")
    print(f"  Active sessions: {stats.get('active_sessions', 0)}")
    print(f"  Supported entities: {len(stats.get('supported_entities', []))}")
    print(f"  Mapping expiry: {stats.get('mapping_expiry_hours', 24)} hours")
    
    print("\nSupported Entity Types:")
    for entity in stats.get('supported_entities', []):
        print(f"  - {entity}")
    
    logger.info("Displayed redaction statistics")


def main():
    """Main demo function."""
    logger = setup_logging()
    logger.info("Starting PII redaction demo")
    
    print("PII/PHI REDACTION SERVICE DEMO")
    print("Microsoft Presidio-based redaction for medical conversations")
    
    try:
        # Initialize the redaction service
        print("\nInitializing PII redaction service...")
        service = PIIRedactionService(logger=logger)
        print("✓ Service initialized successfully")
        
        # Run demos
        demo_basic_redaction(service, logger)
        demo_de_anonymization(service, logger)
        demo_accuracy_validation(service, logger)
        demo_statistics(service, logger)
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        print("Check 'pii_redaction_demo.log' for detailed logs")
        
        logger.info("PII redaction demo completed successfully")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())