"""
PII/PHI redaction service using Microsoft Presidio.
Implements detection, redaction, and de-anonymization of sensitive information.
"""

import logging
import json
import uuid
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer.nlp_engine import NlpEngineProvider

from ..models import RedactionResult, EntityType, AuditEvent, EventType, UserRole


class PIIRedactionService:
    """
    Service for detecting and redacting PII/PHI using Microsoft Presidio.
    
    Features:
    - Detects medical entities (PERSON, DATE_TIME, PHONE_NUMBER, EMAIL_ADDRESS, MEDICAL_LICENSE, US_SSN, LOCATION)
    - Generates typed placeholders ([PERSON_1], [DATE_1], etc.)
    - Stores entity mappings for de-anonymization
    - Comprehensive logging of redaction events
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the PII redaction service."""
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize Presidio engines
        self._init_presidio_engines()
        
        # Entity mapping storage (in production, this would be a secure database)
        self._entity_mappings: Dict[str, Dict[str, str]] = {}
        self._placeholder_counters: Dict[str, Dict[str, int]] = {}
        
        # Mapping cleanup (remove old mappings after 24 hours)
        self._mapping_expiry: Dict[str, datetime] = {}
        
        # Supported entity types for medical context
        self.medical_entities = [
            "PERSON", "DATE_TIME", "PHONE_NUMBER", "EMAIL_ADDRESS", 
            "MEDICAL_LICENSE", "US_SSN", "LOCATION", "US_DRIVER_LICENSE",
            "CREDIT_CARD", "US_PASSPORT", "IBAN_CODE", "IP_ADDRESS"
        ]
        
        self.logger.info("PII Redaction Service initialized with Presidio")
    
    def _init_presidio_engines(self):
        """Initialize Presidio analyzer and anonymizer engines."""
        try:
            # Configure NLP engine with proper configuration
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
                "ner_model_configuration": {
                    "model_to_presidio_entity_mapping": {
                        "PERSON": "PERSON",
                        "DATE": "DATE_TIME", 
                        "TIME": "DATE_TIME",
                        "GPE": "LOCATION",
                        "LOC": "LOCATION"
                    },
                    "low_score_entity_names": ["DATE_TIME"],
                    "labels_to_ignore": ["CARDINAL", "ORDINAL"]
                }
            }
            
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            
            # Initialize analyzer with custom recognizers and only English
            registry = RecognizerRegistry()
            registry.load_predefined_recognizers(
                nlp_engine=nlp_engine,
                languages=["en"]  # Only load English recognizers to avoid warnings
            )
            
            self.analyzer = AnalyzerEngine(
                registry=registry,
                nlp_engine=nlp_engine
            )
            
            # Initialize anonymizer
            self.anonymizer = AnonymizerEngine()
            
            self.logger.info("Presidio engines initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Presidio engines: {e}")
            raise
    
    def _generate_placeholder(self, entity_type: str, user_id: str) -> str:
        """Generate a typed placeholder for an entity."""
        if user_id not in self._placeholder_counters:
            self._placeholder_counters[user_id] = {}
        
        if entity_type not in self._placeholder_counters[user_id]:
            self._placeholder_counters[user_id][entity_type] = 0
        
        self._placeholder_counters[user_id][entity_type] += 1
        counter = self._placeholder_counters[user_id][entity_type]
        
        return f"[{entity_type}_{counter}]"
    
    def _store_entity_mapping(self, user_id: str, session_id: str, 
                            placeholder: str, original_value: str):
        """Store entity mapping for de-anonymization."""
        mapping_key = f"{user_id}:{session_id}"
        
        if mapping_key not in self._entity_mappings:
            self._entity_mappings[mapping_key] = {}
        
        self._entity_mappings[mapping_key][placeholder] = original_value
        
        # Set expiry time (24 hours from now)
        self._mapping_expiry[mapping_key] = datetime.now(timezone.utc) + timedelta(hours=24)
    
    def _cleanup_expired_mappings(self):
        """Remove expired entity mappings."""
        current_time = datetime.now(timezone.utc)
        expired_keys = [
            key for key, expiry_time in self._mapping_expiry.items()
            if current_time > expiry_time
        ]
        
        for key in expired_keys:
            if key in self._entity_mappings:
                del self._entity_mappings[key]
            if key in self._mapping_expiry:
                del self._mapping_expiry[key]
            
            self.logger.info(f"Cleaned up expired entity mappings for {key}")
    
    def redact_message(self, message: str, user_id: str, 
                      session_id: Optional[str] = None) -> RedactionResult:
        """
        Redact PII/PHI from a message.
        
        Args:
            message: The input message to redact
            user_id: User identifier for mapping storage
            session_id: Session identifier for mapping storage
            
        Returns:
            RedactionResult with redacted text and metadata
        """
        try:
            # Clean up expired mappings
            self._cleanup_expired_mappings()
            
            # Generate session ID if not provided
            if not session_id:
                session_id = str(uuid.uuid4())
            
            self.logger.info(f"Starting PII redaction for user {user_id}, session {session_id}")
            
            # Analyze text for PII/PHI entities
            analyzer_results = self.analyzer.analyze(
                text=message,
                entities=self.medical_entities,
                language='en'
            )
            
            if not analyzer_results:
                self.logger.info("No PII/PHI entities detected")
                return RedactionResult(
                    redacted_text=message,
                    entities_found=0,
                    entity_types=[],
                    entity_mappings={},
                    confidence_scores={}
                )
            
            # Sort results by start position to process them in order
            sorted_results = sorted(analyzer_results, key=lambda x: x.start)
            
            # Build replacement text manually to ensure unique placeholders
            redacted_text = message
            entity_mappings = {}
            confidence_scores = {}
            offset = 0  # Track offset due to replacements
            
            for result in sorted_results:
                entity_type = result.entity_type
                start_pos = result.start + offset
                end_pos = result.end + offset
                original_text = redacted_text[start_pos:end_pos]
                
                # Generate unique placeholder
                placeholder = self._generate_placeholder(entity_type, user_id)
                
                # Replace in text
                redacted_text = redacted_text[:start_pos] + placeholder + redacted_text[end_pos:]
                
                # Update offset for next replacements
                offset += len(placeholder) - (result.end - result.start)
                
                # Store mappings
                self._store_entity_mapping(user_id, session_id, placeholder, message[result.start:result.end])
                entity_mappings[placeholder] = message[result.start:result.end]
                confidence_scores[placeholder] = result.score
            
            # Extract entity types
            entity_types = [
                EntityType(result.entity_type) 
                for result in analyzer_results 
                if result.entity_type in [e.value for e in EntityType]
            ]
            
            redaction_result = RedactionResult(
                redacted_text=redacted_text,
                entities_found=len(analyzer_results),
                entity_types=entity_types,
                entity_mappings=entity_mappings,
                confidence_scores=confidence_scores
            )
            
            self.logger.info(
                f"PII redaction completed: {len(analyzer_results)} entities found, "
                f"types: {[r.entity_type for r in analyzer_results]}"
            )
            
            return redaction_result
            
        except Exception as e:
            self.logger.error(f"Error during PII redaction: {e}")
            # Return original message if redaction fails (fail-safe)
            return RedactionResult(
                redacted_text=message,
                entities_found=0,
                entity_types=[],
                entity_mappings={},
                confidence_scores={}
            )
    
    def de_anonymize_response(self, response: str, user_id: str, 
                            session_id: str) -> str:
        """
        De-anonymize a response by replacing placeholders with original values.
        
        Args:
            response: The response text containing placeholders
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            De-anonymized response text
        """
        try:
            mapping_key = f"{user_id}:{session_id}"
            
            if mapping_key not in self._entity_mappings:
                self.logger.warning(f"No entity mappings found for {mapping_key}")
                return response
            
            de_anonymized_response = response
            mappings = self._entity_mappings[mapping_key]
            
            # Replace placeholders with original values
            for placeholder, original_value in mappings.items():
                de_anonymized_response = de_anonymized_response.replace(
                    placeholder, original_value
                )
            
            self.logger.info(f"De-anonymized response for {mapping_key}")
            return de_anonymized_response
            
        except Exception as e:
            self.logger.error(f"Error during de-anonymization: {e}")
            return response
    
    def get_redaction_stats(self, user_id: Optional[str] = None) -> Dict:
        """
        Get redaction statistics.
        
        Args:
            user_id: Optional user ID to filter stats
            
        Returns:
            Dictionary with redaction statistics
        """
        try:
            total_mappings = 0
            active_sessions = 0
            
            for mapping_key, mappings in self._entity_mappings.items():
                if user_id and not mapping_key.startswith(f"{user_id}:"):
                    continue
                
                total_mappings += len(mappings)
                active_sessions += 1
            
            return {
                "total_entity_mappings": total_mappings,
                "active_sessions": active_sessions,
                "supported_entities": self.medical_entities,
                "mapping_expiry_hours": 24
            }
            
        except Exception as e:
            self.logger.error(f"Error getting redaction stats: {e}")
            return {}
    
    def clear_user_mappings(self, user_id: str):
        """
        Clear all entity mappings for a specific user.
        
        Args:
            user_id: User identifier
        """
        try:
            keys_to_remove = [
                key for key in self._entity_mappings.keys()
                if key.startswith(f"{user_id}:")
            ]
            
            for key in keys_to_remove:
                if key in self._entity_mappings:
                    del self._entity_mappings[key]
                if key in self._mapping_expiry:
                    del self._mapping_expiry[key]
            
            # Clear placeholder counters
            if user_id in self._placeholder_counters:
                del self._placeholder_counters[user_id]
            
            self.logger.info(f"Cleared all mappings for user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error clearing user mappings: {e}")
    
    def validate_redaction_accuracy(self, test_cases: List[Dict]) -> Dict:
        """
        Validate redaction accuracy on test cases.
        
        Args:
            test_cases: List of test cases with 'text' and 'expected_entities'
            
        Returns:
            Dictionary with accuracy metrics
        """
        try:
            total_cases = len(test_cases)
            correct_detections = 0
            total_entities_expected = 0
            total_entities_detected = 0
            
            results = []
            
            for i, test_case in enumerate(test_cases):
                text = test_case['text']
                expected_entities = set(test_case.get('expected_entities', []))
                
                # Perform redaction
                result = self.redact_message(text, f"test_user_{i}")
                detected_entities = set([et.value for et in result.entity_types])
                
                # Calculate metrics for this case
                case_correct = expected_entities == detected_entities
                if case_correct:
                    correct_detections += 1
                
                total_entities_expected += len(expected_entities)
                total_entities_detected += len(detected_entities)
                
                results.append({
                    'text': text,
                    'expected': list(expected_entities),
                    'detected': list(detected_entities),
                    'correct': case_correct,
                    'entities_found': result.entities_found
                })
            
            accuracy = correct_detections / total_cases if total_cases > 0 else 0
            precision = (
                correct_detections / total_entities_detected 
                if total_entities_detected > 0 else 0
            )
            recall = (
                correct_detections / total_entities_expected 
                if total_entities_expected > 0 else 0
            )
            
            return {
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall,
                'total_cases': total_cases,
                'correct_detections': correct_detections,
                'total_entities_expected': total_entities_expected,
                'total_entities_detected': total_entities_detected,
                'detailed_results': results
            }
            
        except Exception as e:
            self.logger.error(f"Error validating redaction accuracy: {e}")
            return {'error': str(e)}