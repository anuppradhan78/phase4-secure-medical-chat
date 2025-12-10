"""
Pydantic models for the Secure Medical Chat system.
Defines data structures for redaction, validation, cost tracking, and audit events.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class EntityType(str, Enum):
    """Enumeration of PII/PHI entity types that can be detected."""
    PERSON = "PERSON"
    DATE_TIME = "DATE_TIME"
    PHONE_NUMBER = "PHONE_NUMBER"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    US_SSN = "US_SSN"
    LOCATION = "LOCATION"
    MEDICAL_RECORD_NUMBER = "MEDICAL_RECORD_NUMBER"


class UserRole(str, Enum):
    """User roles for RBAC."""
    PATIENT = "patient"
    PHYSICIAN = "physician"
    ADMIN = "admin"


class ThreatType(str, Enum):
    """Types of security threats that can be detected."""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    PII_EXTRACTION = "pii_extraction"
    UNSAFE_CONTENT = "unsafe_content"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class EventType(str, Enum):
    """Types of audit events."""
    CHAT_REQUEST = "chat_request"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    PII_REDACTION = "pii_redaction"
    SECURITY_BLOCK = "security_block"
    COST_TRACKING = "cost_tracking"


class RedactionResult(BaseModel):
    """Result of PII/PHI redaction process."""
    redacted_text: str = Field(..., description="Text with PII/PHI replaced by placeholders")
    entities_found: int = Field(..., description="Number of entities detected and redacted")
    entity_types: List[EntityType] = Field(default_factory=list, description="Types of entities found")
    entity_mappings: Dict[str, str] = Field(default_factory=dict, description="Mapping of placeholders to original values")
    confidence_scores: Dict[str, float] = Field(default_factory=dict, description="Confidence scores for detected entities")


class ValidationResult(BaseModel):
    """Result of input/output validation through guardrails."""
    blocked: bool = Field(..., description="Whether the content was blocked")
    reason: Optional[str] = Field(None, description="Reason for blocking if applicable")
    threat_type: Optional[ThreatType] = Field(None, description="Type of threat detected")
    risk_score: float = Field(default=0.0, description="Risk score from 0.0 to 1.0")
    modified_response: Optional[str] = Field(None, description="Modified response if content was altered")
    guardrail_flags: List[str] = Field(default_factory=list, description="List of guardrail flags triggered")


class ModelConfig(BaseModel):
    """Configuration for LLM model selection."""
    model: str = Field(..., description="Model name (e.g., gpt-3.5-turbo, gpt-4)")
    max_tokens: int = Field(default=1000, description="Maximum tokens for response")
    temperature: float = Field(default=0.7, description="Temperature for response generation")
    provider: str = Field(default="openai", description="LLM provider")


class CostData(BaseModel):
    """Cost tracking data for LLM usage."""
    model: str = Field(..., description="Model used for the request")
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    total_tokens: int = Field(..., description="Total tokens used")
    cost_usd: float = Field(..., description="Cost in USD")
    user_role: UserRole = Field(..., description="Role of the user making the request")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of the request")
    session_id: Optional[str] = Field(None, description="Session ID if available")
    cache_hit: bool = Field(default=False, description="Whether response was served from cache")


class AuditEvent(BaseModel):
    """Audit event for logging system interactions."""
    event_id: Optional[str] = Field(None, description="Unique event identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    user_id: Optional[str] = Field(None, description="User identifier")
    user_role: UserRole = Field(..., description="User role")
    session_id: Optional[str] = Field(None, description="Session identifier")
    event_type: EventType = Field(..., description="Type of event")
    message: Optional[str] = Field(None, description="Original user message (redacted)")
    response: Optional[str] = Field(None, description="System response")
    cost_usd: Optional[float] = Field(None, description="Cost of the operation")
    latency_ms: Optional[int] = Field(None, description="Latency in milliseconds")
    entities_redacted: List[EntityType] = Field(default_factory=list, description="Types of entities redacted")
    security_flags: List[str] = Field(default_factory=list, description="Security flags raised")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SecurityEvent(BaseModel):
    """Security event for logging threats and blocks."""
    event_id: Optional[str] = Field(None, description="Unique event identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp")
    user_id: Optional[str] = Field(None, description="User identifier")
    user_role: Optional[UserRole] = Field(None, description="User role")
    session_id: Optional[str] = Field(None, description="Session identifier")
    threat_type: ThreatType = Field(..., description="Type of threat detected")
    blocked_content: str = Field(..., description="Content that was blocked (sanitized)")
    risk_score: float = Field(..., description="Risk score from 0.0 to 1.0")
    detection_method: str = Field(..., description="Method used to detect the threat")
    action_taken: str = Field(..., description="Action taken in response")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class UserSession(BaseModel):
    """User session data."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    user_role: UserRole = Field(..., description="User role")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Session creation time")
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last activity timestamp")
    expires_at: datetime = Field(..., description="Session expiration time")
    is_active: bool = Field(default=True, description="Whether session is active")
    request_count: int = Field(default=0, description="Number of requests in this session")
    total_cost_usd: float = Field(default=0.0, description="Total cost for this session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional session metadata")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., description="User message", min_length=1, max_length=10000)
    user_role: UserRole = Field(..., description="User role")
    session_id: Optional[str] = Field(None, description="Session ID")
    user_id: Optional[str] = Field(None, description="User ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional request metadata")


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="AI response")
    metadata: Dict[str, Any] = Field(..., description="Response metadata including cost, latency, etc.")


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""
    total_cost_usd: float = Field(..., description="Total cost in USD")
    queries_today: int = Field(..., description="Number of queries today")
    cache_hit_rate: float = Field(..., description="Cache hit rate (0.0 to 1.0)")
    avg_latency_ms: float = Field(..., description="Average latency in milliseconds")
    cost_by_model: Dict[str, float] = Field(..., description="Cost breakdown by model")
    cost_by_role: Dict[str, float] = Field(..., description="Cost breakdown by user role")
    security_events_today: int = Field(..., description="Number of security events today")