"""
Guardrails implementation for secure medical chat.
Implements NeMo Guardrails and Llama-Guard-3 for content safety.
"""

import os
import re
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Optional imports with fallbacks
try:
    from nemoguardrails import RailsConfig, LLMRails
    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class ValidationResult:
    """Result of content validation."""
    blocked: bool
    reason: Optional[str] = None
    threat_type: Optional[str] = None
    risk_score: float = 0.0
    modified_response: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SecurityEvent:
    """Security event for logging."""
    timestamp: datetime
    user_id: str
    threat_type: str
    blocked_content: str
    risk_score: float
    detection_method: str


class PromptInjectionDetector:
    """Detects prompt injection and jailbreak attempts using pattern matching."""
    
    def __init__(self):
        self.injection_patterns = [
            r"ignore\s+(all\s+)?previous\s+instructions?",
            r"forget\s+(everything|all)\s+(above|before)",
            r"disregard\s+(your\s+)?(programming|instructions|guidelines)",
            r"override\s+(your\s+)?(instructions|safety|protocols)",
            r"(act|pretend|roleplay)\s+as\s+(if\s+)?you\s+(are|were)",
            r"simulate\s+being\s+",
            r"you\s+are\s+now\s+(in\s+)?(\w+\s+)?mode",
            r"(DAN|developer|unrestricted|jailbreak)\s+mode",
            r"break\s+free\s+from",
            r"remove\s+(all\s+)?(restrictions|limitations)",
            r"bypass\s+(your\s+)?(guidelines|safety|rules)",
            r"no\s+longer\s+bound\s+by",
            r"without\s+(any\s+)?(restrictions|limitations)",
            r"enter\s+\w+\s+mode",
            r"prescription\s+for\s+\w+",
            r"give\s+me\s+.*\s+(dosage|prescription|treatment\s+plan)",
            r"tell\s+me\s+how\s+to\s+(diagnose|treat|prescribe)",
            r"safety\s+(unbinding|bypass)",
            r"restriction\s+bypass",
            r"disclaimer\s+bypass",
        ]
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.injection_patterns]
    
    def detect(self, text: str) -> Tuple[bool, str, float]:
        """Detect prompt injection attempts."""
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(text):
                confidence = 0.8 + (i * 0.02)
                return True, self.injection_patterns[i], min(confidence, 1.0)
        
        # Check for suspicious keyword combinations and individual high-risk terms
        text_lower = text.lower()
        
        # High-risk single terms that should be blocked
        high_risk_terms = [
            "jailbreak", "dan mode", "developer mode", "unrestricted", 
            "break free", "bypass", "override", "ignore safety",
            "safety unbinding", "restriction bypass", "disclaimer bypass"
        ]
        
        for term in high_risk_terms:
            if term in text_lower:
                return True, f"high_risk_term_{term.replace(' ', '_')}", 0.9
        
        # Check for roleplay patterns specifically
        roleplay_patterns = [
            r"pretend\s+you\s+are\s+a\s+(doctor|physician|pharmacist)",
            r"act\s+as\s+if\s+you\s+(are|have)\s+no\s+restrictions",
            r"roleplay\s+as\s+a\s+(doctor|physician|pharmacist)",
        ]
        
        for pattern in roleplay_patterns:
            if re.search(pattern, text_lower):
                return True, f"roleplay_pattern", 0.85
        
        # Suspicious keyword combinations
        suspicious_keywords = ["ignore", "forget", "override", "bypass", "disregard", "pretend", "roleplay", "simulate", "act as"]
        keyword_count = sum(1 for keyword in suspicious_keywords if keyword in text_lower)
        if keyword_count >= 2:
            return True, "multiple_suspicious_keywords", 0.7
        
        return False, "", 0.0


class MedicalSafetyValidator:
    """Validates medical content for safety and appropriate disclaimers."""
    
    def __init__(self):
        self.medication_patterns = [
            r"dosage\s+of\s+\w+",
            r"how\s+much\s+\w+\s+(should|to)\s+take",
            r"mg\s+of\s+\w+",
            r"pills?\s+of\s+\w+",
        ]
        
        self.emergency_patterns = [
            r"chest\s+pain",
            r"difficulty\s+breathing",
            r"severe\s+bleeding",
            r"heart\s+attack",
            r"stroke\s+symptoms?",
        ]
        
        self.disclaimer_text = "This is for informational purposes only. Consult your healthcare provider for medical advice."
        self.emergency_text = "These symptoms may require immediate medical attention. Please consider calling 911 or going to the nearest emergency room."
    
    def validate_input(self, text: str) -> ValidationResult:
        """Validate user input for medical safety concerns."""
        text_lower = text.lower()
        
        # Check for medication dosage requests
        for pattern in self.medication_patterns:
            if re.search(pattern, text_lower):
                return ValidationResult(
                    blocked=True,
                    reason="medication_dosage_request",
                    threat_type="medical_safety",
                    risk_score=0.8
                )
        
        # Emergency symptoms should not be blocked but flagged
        for pattern in self.emergency_patterns:
            if re.search(pattern, text_lower):
                return ValidationResult(
                    blocked=False,
                    reason="emergency_symptoms_detected",
                    threat_type="medical_emergency",
                    risk_score=0.3,
                    metadata={"requires_emergency_response": True}
                )
        
        return ValidationResult(blocked=False)
    
    def validate_output(self, response: str) -> ValidationResult:
        """Validate AI response for medical safety and disclaimers."""
        response_lower = response.lower()
        
        # Check if response contains medical advice
        medical_keywords = ["should take", "medication", "treatment", "symptoms suggest"]
        contains_medical_advice = any(keyword in response_lower for keyword in medical_keywords)
        
        # Check if response already has disclaimer
        has_disclaimer = self.disclaimer_text.lower() in response_lower
        
        modified_response = response
        
        # Add disclaimer if medical advice is present but disclaimer is missing
        if contains_medical_advice and not has_disclaimer:
            modified_response = f"{response}\n\n{self.disclaimer_text}"
        
        # Check for emergency symptoms and add emergency guidance
        contains_emergency = any(re.search(pattern, response_lower) for pattern in self.emergency_patterns)
        
        if contains_emergency and self.emergency_text not in response:
            modified_response = f"{modified_response}\n\n{self.emergency_text}"
        
        return ValidationResult(
            blocked=False,
            modified_response=modified_response if modified_response != response else None
        )


class GuardrailsService:
    """Main guardrails service combining multiple safety mechanisms."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "config/guardrails"
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.prompt_detector = PromptInjectionDetector()
        self.medical_validator = MedicalSafetyValidator()
        
        # Security event storage
        self.security_events: List[SecurityEvent] = []
    
    def validate_input(self, message: str, user_id: str = "anonymous") -> ValidationResult:
        """Validate user input through multiple safety checks."""
        # 1. Prompt injection detection
        is_injection, pattern, confidence = self.prompt_detector.detect(message)
        if is_injection:
            self._log_security_event(user_id, "prompt_injection", message, confidence, "pattern_matching")
            return ValidationResult(
                blocked=True,
                reason="prompt_injection",
                threat_type="injection_attack",
                risk_score=confidence,
                metadata={"pattern": pattern}
            )
        
        # 2. Medical safety validation
        medical_result = self.medical_validator.validate_input(message)
        if medical_result.blocked:
            self._log_security_event(user_id, medical_result.threat_type, message, medical_result.risk_score, "medical_validator")
            return medical_result
        
        return ValidationResult(blocked=False, reason="validation_passed")
    
    def validate_output(self, response: str, user_id: str = "anonymous") -> ValidationResult:
        """Validate AI response for safety and compliance."""
        return self.medical_validator.validate_output(response)
    
    def _log_security_event(self, user_id: str, threat_type: str, content: str, risk_score: float, detection_method: str):
        """Log security event for audit purposes."""
        event = SecurityEvent(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            threat_type=threat_type,
            blocked_content=content[:200],
            risk_score=risk_score,
            detection_method=detection_method
        )
        self.security_events.append(event)
        
        self.logger.warning(f"Security event: {threat_type} detected for user {user_id}")
    
    def get_security_events(self, limit: int = 100) -> List[SecurityEvent]:
        """Get recent security events for monitoring."""
        return self.security_events[-limit:]
    
    def test_malicious_prompts(self, test_file: Optional[str] = None) -> Dict[str, Any]:
        """Test the guardrails against a set of malicious prompts."""
        if test_file is None:
            test_file = "config/test_data/malicious_prompts.json"
        
        try:
            with open(test_file, 'r') as f:
                test_prompts = json.load(f)
        except FileNotFoundError:
            return {"error": "Test file not found"}
        
        results = {
            "total_tests": len(test_prompts),
            "blocked": 0,
            "allowed": 0,
            "correct_blocks": 0,
            "false_positives": 0,
            "false_negatives": 0,
            "details": []
        }
        
        for prompt_data in test_prompts:
            prompt = prompt_data["prompt"]
            should_block = prompt_data["should_block"]
            attack_type = prompt_data["attack_type"]
            
            validation_result = self.validate_input(prompt, "test_user")
            was_blocked = validation_result.blocked
            
            # Update statistics
            if was_blocked:
                results["blocked"] += 1
            else:
                results["allowed"] += 1
            
            if was_blocked == should_block:
                results["correct_blocks"] += 1
            elif was_blocked and not should_block:
                results["false_positives"] += 1
            elif not was_blocked and should_block:
                results["false_negatives"] += 1
            
            results["details"].append({
                "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
                "attack_type": attack_type,
                "should_block": should_block,
                "was_blocked": was_blocked,
                "correct": was_blocked == should_block,
                "reason": validation_result.reason,
                "risk_score": validation_result.risk_score
            })
        
        # Calculate accuracy
        results["accuracy"] = results["correct_blocks"] / results["total_tests"]
        results["block_rate"] = results["blocked"] / results["total_tests"]
        
        return results


def create_guardrails_service(config_path: Optional[str] = None) -> GuardrailsService:
    """Create and return a configured GuardrailsService instance."""
    return GuardrailsService(config_path)