"""
Medical safety controls for secure medical chat.
Implements automatic disclaimers, emergency detection, and medical knowledge grounding.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ..models import ValidationResult, ThreatType


@dataclass
class MedicalKnowledgeEntry:
    """Entry in the medical knowledge base."""
    condition: str
    symptoms: List[str]
    emergency_indicators: List[str]
    general_info: str
    sources: List[str]
    disclaimer_required: bool = True


@dataclass
class EmergencyResponse:
    """Emergency response recommendation."""
    is_emergency: bool
    urgency_level: str  # "immediate", "urgent", "routine"
    recommendation: str
    call_911: bool = False


class MedicalKnowledgeBase:
    """Simple medical knowledge base for grounded responses."""
    
    def __init__(self):
        self.knowledge_entries: Dict[str, MedicalKnowledgeEntry] = {}
        self._load_medical_knowledge()
    
    def _load_medical_knowledge(self):
        """Load basic medical knowledge entries."""
        entries = [
            MedicalKnowledgeEntry(
                condition="chest_pain",
                symptoms=["chest pain", "chest discomfort", "pressure in chest"],
                emergency_indicators=["severe chest pain", "crushing chest pain"],
                general_info="Chest pain can have many causes, from muscle strain to serious heart conditions.",
                sources=["American Heart Association", "Mayo Clinic"],
                disclaimer_required=True
            ),
            MedicalKnowledgeEntry(
                condition="shortness_of_breath",
                symptoms=["shortness of breath", "difficulty breathing", "breathlessness"],
                emergency_indicators=["severe difficulty breathing", "cannot speak"],
                general_info="Shortness of breath can be caused by various conditions affecting the heart, lungs, or other systems.",
                sources=["American Lung Association", "Cleveland Clinic"],
                disclaimer_required=True
            ),
            MedicalKnowledgeEntry(
                condition="headache",
                symptoms=["headache", "head pain", "migraine"],
                emergency_indicators=["sudden severe headache", "worst headache of life"],
                general_info="Headaches are common and usually not serious, but some patterns require medical attention.",
                sources=["National Institute of Neurological Disorders", "Mayo Clinic"],
                disclaimer_required=True
            )
        ]
        
        for entry in entries:
            self.knowledge_entries[entry.condition] = entry
    
    def find_relevant_conditions(self, text: str) -> List[MedicalKnowledgeEntry]:
        """Find medical conditions mentioned in the text."""
        text_lower = text.lower()
        relevant_conditions = []
        
        for condition, entry in self.knowledge_entries.items():
            for symptom in entry.symptoms:
                if symptom.lower() in text_lower:
                    relevant_conditions.append(entry)
                    break
        
        return relevant_conditions


class EmergencyDetector:
    """Detects emergency medical situations and provides appropriate responses."""
    
    def __init__(self):
        self.emergency_patterns = [
            "chest pain severe",
            "chest pain crushing", 
            "heart attack",
            "can't breathe",
            "difficulty breathing",
            "shortness of breath",
            "severe bleeding",
            "stroke symptoms",
            "sudden severe headache",
            "loss of consciousness",
            "seizure"
        ]
        
        self.urgent_patterns = [
            "high fever",
            "persistent vomiting", 
            "severe abdominal pain"
        ]
    
    def assess_emergency_level(self, text: str) -> EmergencyResponse:
        """Assess the emergency level of the described symptoms."""
        text_lower = text.lower()
        
        # Check for immediate emergency patterns
        for pattern in self.emergency_patterns:
            if pattern in text_lower:
                return EmergencyResponse(
                    is_emergency=True,
                    urgency_level="immediate",
                    recommendation="These symptoms may indicate a medical emergency. Call 911 or go to the nearest emergency room immediately.",
                    call_911=True
                )
        
        # Check for urgent patterns
        for pattern in self.urgent_patterns:
            if pattern in text_lower:
                return EmergencyResponse(
                    is_emergency=True,
                    urgency_level="urgent",
                    recommendation="These symptoms require prompt medical attention. Contact your healthcare provider or consider urgent care.",
                    call_911=False
                )
        
        # Check for general medical concerns
        medical_keywords = ["pain", "symptoms", "feel sick", "not feeling well"]
        if any(keyword in text_lower for keyword in medical_keywords):
            return EmergencyResponse(
                is_emergency=False,
                urgency_level="routine",
                recommendation="For any health concerns, it's best to consult with your healthcare provider.",
                call_911=False
            )
        
        return EmergencyResponse(
            is_emergency=False,
            urgency_level="none",
            recommendation="",
            call_911=False
        )


class MedicalDisclaimerManager:
    """Manages medical disclaimers and safety warnings."""
    
    def __init__(self):
        self.standard_disclaimer = (
            "This information is for educational purposes only and is not intended as medical advice. "
            "Always consult your healthcare provider for medical advice, diagnosis, or treatment."
        )
        
        self.medication_disclaimer = (
            "I cannot provide specific medication dosages or prescriptions. "
            "Only licensed healthcare providers can prescribe medications and determine appropriate dosages. "
            "Please consult your doctor or pharmacist for medication information."
        )
        
        self.medical_advice_keywords = [
            "you should take",
            "recommended treatment", 
            "diagnosis is",
            "symptoms suggest"
        ]
        
        self.medication_keywords = [
            "dosage",
            "how much to take",
            "mg of",
            "prescription"
        ]
    
    def needs_disclaimer(self, text: str) -> Tuple[bool, str]:
        """Check if text needs a medical disclaimer and return appropriate disclaimer."""
        text_lower = text.lower()
        
        # Check for medication-related content
        for keyword in self.medication_keywords:
            if keyword in text_lower:
                return True, self.medication_disclaimer
        
        # Check for medical advice patterns
        for keyword in self.medical_advice_keywords:
            if keyword in text_lower:
                return True, self.standard_disclaimer
        
        # Check for general medical keywords
        medical_keywords = ["symptoms", "treatment", "diagnosis", "condition", "disease", "medication", "medical", "health"]
        if any(keyword in text_lower for keyword in medical_keywords):
            return True, self.standard_disclaimer
        
        return False, ""
    
    def add_disclaimer(self, text: str, disclaimer_type: str = "standard") -> str:
        """Add appropriate disclaimer to text."""
        disclaimers = {
            "standard": self.standard_disclaimer,
            "medication": self.medication_disclaimer
        }
        
        disclaimer = disclaimers.get(disclaimer_type, self.standard_disclaimer)
        
        # Check if disclaimer already exists
        if disclaimer.lower() in text.lower():
            return text
        
        return f"{text}\n\n{disclaimer}"


class MedicalSourceCitationManager:
    """Manages medical source citations for grounded responses."""
    
    def __init__(self):
        self.trusted_sources = {
            "mayo_clinic": "Mayo Clinic",
            "cdc": "Centers for Disease Control and Prevention (CDC)",
            "nih": "National Institutes of Health (NIH)",
            "aha": "American Heart Association",
            "ala": "American Lung Association"
        }
    
    def add_source_citation(self, text: str, sources: List[str]) -> str:
        """Add source citations to medical information."""
        if not sources:
            return text
        
        formatted_sources = []
        for source in sources:
            source_key = source.lower().replace(" ", "_")
            if source_key in self.trusted_sources:
                formatted_sources.append(self.trusted_sources[source_key])
            else:
                formatted_sources.append(source)
        
        if formatted_sources:
            citation = f"\n\nSources: {', '.join(formatted_sources)}"
            return f"{text}{citation}"
        
        return text


class MedicalSafetyController:
    """Main controller for medical safety controls."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize components
        self.knowledge_base = MedicalKnowledgeBase()
        self.emergency_detector = EmergencyDetector()
        self.disclaimer_manager = MedicalDisclaimerManager()
        self.citation_manager = MedicalSourceCitationManager()
        
        self.logger.info("Medical Safety Controller initialized")
    
    def validate_input(self, message: str, user_id: str = "anonymous") -> ValidationResult:
        """Validate user input for medical safety concerns."""
        # Check for medication dosage requests (should be blocked)
        if self._contains_medication_request(message):
            return ValidationResult(
                blocked=True,
                reason="medication_dosage_request",
                threat_type=ThreatType.UNSAFE_CONTENT,
                risk_score=0.8,
                guardrail_flags=["medication_request_blocked"]
            )
        
        # Check for emergency situations (not blocked, but flagged)
        emergency_response = self.emergency_detector.assess_emergency_level(message)
        if emergency_response.is_emergency:
            return ValidationResult(
                blocked=False,
                reason="emergency_detected",
                threat_type=None,
                risk_score=0.3,
                guardrail_flags=[f"emergency_{emergency_response.urgency_level}"]
            )
        
        return ValidationResult(blocked=False, reason="medical_safety_passed")
    
    def enhance_response(self, response: str, original_message: str) -> str:
        """Enhance AI response with medical safety controls."""
        enhanced_response = response
        
        # 1. Check for emergency situations and add emergency guidance
        emergency_response = self.emergency_detector.assess_emergency_level(original_message)
        if emergency_response.is_emergency and emergency_response.recommendation:
            enhanced_response = f"{enhanced_response}\n\n⚠️ IMPORTANT: {emergency_response.recommendation}"
        
        # 2. Find relevant medical conditions and add grounded information
        relevant_conditions = self.knowledge_base.find_relevant_conditions(original_message)
        if relevant_conditions:
            for condition in relevant_conditions[:2]:  # Limit to 2 conditions
                if condition.general_info and condition.general_info.lower() not in enhanced_response.lower():
                    enhanced_response = f"{enhanced_response}\n\nAdditional information: {condition.general_info}"
                
                # Add source citations
                if condition.sources:
                    enhanced_response = self.citation_manager.add_source_citation(
                        enhanced_response, condition.sources
                    )
        
        # 3. Add medical disclaimers
        needs_disclaimer, disclaimer = self.disclaimer_manager.needs_disclaimer(enhanced_response)
        if needs_disclaimer:
            enhanced_response = self.disclaimer_manager.add_disclaimer(enhanced_response)
        
        return enhanced_response
    
    def _contains_medication_request(self, text: str) -> bool:
        """Check if text contains requests for specific medication dosages."""
        text_lower = text.lower()
        
        medication_request_patterns = [
            "how much",
            "what dosage",
            "how many mg",
            "prescription for",
            "dosage of"
        ]
        
        # Common medication names to check for
        medication_names = [
            "ibuprofen", "aspirin", "tylenol", "acetaminophen", "advil", "motrin",
            "medication", "medicine", "drug", "pill", "tablet"
        ]
        
        # Check if it's asking about medication AND contains dosage-related terms
        has_medication = any(med in text_lower for med in medication_names)
        has_dosage_request = any(pattern in text_lower for pattern in medication_request_patterns)
        
        return has_medication and has_dosage_request
    
    def get_safety_stats(self) -> Dict[str, Any]:
        """Get medical safety statistics."""
        return {
            "knowledge_base_entries": len(self.knowledge_base.knowledge_entries),
            "emergency_patterns": len(self.emergency_detector.emergency_patterns),
            "urgent_patterns": len(self.emergency_detector.urgent_patterns),
            "supported_conditions": list(self.knowledge_base.knowledge_entries.keys()),
            "trusted_sources": len(self.citation_manager.trusted_sources)
        }


def create_medical_safety_controller(logger: Optional[logging.Logger] = None) -> MedicalSafetyController:
    """Create and return a configured MedicalSafetyController instance."""
    return MedicalSafetyController(logger)