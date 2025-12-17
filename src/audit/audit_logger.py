"""
Comprehensive audit logging service for the Secure Medical Chat system.
Handles logging of all user queries, LLM responses, system actions, security events,
and user interactions with comprehensive metadata tracking.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager

try:
    from ..database import DatabaseManager, get_database
    from ..models import (
        AuditEvent, SecurityEvent, UserSession, EventType, ThreatType, 
        UserRole, EntityType, RedactionResult, ValidationResult, CostData
    )
except ImportError:
    # Handle case when running as script or in tests
    from database import DatabaseManager, get_database
    from models import (
        AuditEvent, SecurityEvent, UserSession, EventType, ThreatType,
        UserRole, EntityType, RedactionResult, ValidationResult, CostData
    )

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Comprehensive audit logging service that tracks all system interactions,
    security events, and user activities for compliance and monitoring.
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize audit logger with database manager."""
        self.db = db_manager or get_database()
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for audit events."""
        # Create audit-specific logger
        self.audit_logger = logging.getLogger('audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # Create security-specific logger
        self.security_logger = logging.getLogger('security')
        self.security_logger.setLevel(logging.WARNING)
        
        logger.info("Audit logging system initialized")
    
    def log_chat_interaction(
        self,
        user_id: Optional[str],
        user_role: UserRole,
        session_id: Optional[str],
        original_message: str,
        redacted_message: str,
        response: str,
        redaction_result: Optional[RedactionResult] = None,
        validation_result: Optional[ValidationResult] = None,
        cost_data: Optional[CostData] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a complete chat interaction including all processing steps.
        
        Args:
            user_id: User identifier
            user_role: User role (patient, physician, admin)
            session_id: Session identifier
            original_message: Original user message (for audit trail)
            redacted_message: Message after PII/PHI redaction
            response: System response
            redaction_result: PII/PHI redaction details
            validation_result: Guardrails validation details
            cost_data: Cost tracking information
            latency_ms: Response latency in milliseconds
            metadata: Additional metadata
            
        Returns:
            Event ID for the logged interaction
        """
        # Prepare entities redacted list
        entities_redacted = []
        if redaction_result:
            entities_redacted = redaction_result.entity_types
        
        # Prepare security flags
        security_flags = []
        if validation_result:
            security_flags = validation_result.guardrail_flags
            if validation_result.blocked:
                security_flags.append(f"blocked_{validation_result.reason}")
        
        # Prepare metadata
        full_metadata = metadata or {}
        full_metadata.update({
            'original_message_length': len(original_message),
            'redacted_message_length': len(redacted_message),
            'response_length': len(response),
            'entities_found': redaction_result.entities_found if redaction_result else 0,
            'redaction_confidence': redaction_result.confidence_scores if redaction_result else {},
            'validation_blocked': validation_result.blocked if validation_result else False,
            'validation_risk_score': validation_result.risk_score if validation_result else 0.0,
            'cost_model': cost_data.model if cost_data else None,
            'cost_tokens': cost_data.total_tokens if cost_data else 0,
            'cache_hit': cost_data.cache_hit if cost_data else False
        })
        
        # Create audit event
        event = AuditEvent(
            event_id=f"chat_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role,
            session_id=session_id,
            event_type=EventType.CHAT_REQUEST,
            message=redacted_message,  # Store redacted version for privacy
            response=response,
            cost_usd=cost_data.cost_usd if cost_data else None,
            latency_ms=latency_ms,
            entities_redacted=entities_redacted,
            security_flags=security_flags,
            metadata=full_metadata
        )
        
        # Log to database
        event_id = self.db.log_audit_event(event)
        
        # Log to audit logger
        self.audit_logger.info(
            f"Chat interaction logged - User: {user_id}, Role: {user_role.value}, "
            f"Session: {session_id}, Entities: {len(entities_redacted)}, "
            f"Cost: ${cost_data.cost_usd if cost_data else 0:.4f}, "
            f"Latency: {latency_ms}ms"
        )
        
        return event_id
    
    def log_pii_redaction(
        self,
        user_id: Optional[str],
        user_role: UserRole,
        session_id: Optional[str],
        original_text: str,
        redaction_result: RedactionResult,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log PII/PHI redaction events with detailed entity information.
        
        Args:
            user_id: User identifier
            user_role: User role
            session_id: Session identifier
            original_text: Original text (length only for privacy)
            redaction_result: Detailed redaction results
            metadata: Additional metadata
            
        Returns:
            Event ID for the logged redaction
        """
        # Prepare metadata with redaction details
        full_metadata = metadata or {}
        full_metadata.update({
            'original_text_length': len(original_text),
            'redacted_text_length': len(redaction_result.redacted_text),
            'entities_found': redaction_result.entities_found,
            'entity_mappings_count': len(redaction_result.entity_mappings),
            'confidence_scores': redaction_result.confidence_scores,
            'entity_types_detected': [et.value for et in redaction_result.entity_types]
        })
        
        # Create audit event
        event = AuditEvent(
            event_id=f"redaction_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role,
            session_id=session_id,
            event_type=EventType.PII_REDACTION,
            message=f"Text redaction: {redaction_result.entities_found} entities found",
            entities_redacted=redaction_result.entity_types,
            metadata=full_metadata
        )
        
        # Log to database
        event_id = self.db.log_audit_event(event)
        
        # Log to audit logger
        self.audit_logger.info(
            f"PII redaction logged - User: {user_id}, Entities: {redaction_result.entities_found}, "
            f"Types: {[et.value for et in redaction_result.entity_types]}"
        )
        
        return event_id
    
    def log_security_event(
        self,
        user_id: Optional[str],
        user_role: Optional[UserRole],
        session_id: Optional[str],
        threat_type: ThreatType,
        blocked_content: str,
        risk_score: float,
        detection_method: str,
        action_taken: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log security events including blocked prompts, authentication attempts,
        and access control decisions.
        
        Args:
            user_id: User identifier
            user_role: User role
            session_id: Session identifier
            threat_type: Type of threat detected
            blocked_content: Content that was blocked (sanitized)
            risk_score: Risk score from 0.0 to 1.0
            detection_method: Method used to detect the threat
            action_taken: Action taken in response
            metadata: Additional metadata
            
        Returns:
            Event ID for the logged security event
        """
        # Sanitize blocked content for logging (truncate and remove sensitive data)
        sanitized_content = self._sanitize_content(blocked_content)
        
        # Prepare metadata
        full_metadata = metadata or {}
        full_metadata.update({
            'original_content_length': len(blocked_content),
            'sanitized_content_length': len(sanitized_content),
            'risk_score': risk_score,
            'detection_timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Create security event
        event = SecurityEvent(
            event_id=f"security_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role,
            session_id=session_id,
            threat_type=threat_type,
            blocked_content=sanitized_content,
            risk_score=risk_score,
            detection_method=detection_method,
            action_taken=action_taken,
            metadata=full_metadata
        )
        
        # Log to database
        event_id = self.db.log_security_event(event)
        
        # Log to security logger
        self.security_logger.warning(
            f"Security event logged - User: {user_id}, Threat: {threat_type.value}, "
            f"Risk: {risk_score:.2f}, Action: {action_taken}"
        )
        
        return event_id
    
    def log_authentication_attempt(
        self,
        user_id: Optional[str],
        user_role: Optional[UserRole],
        session_id: Optional[str],
        success: bool,
        method: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log authentication attempts for security monitoring.
        
        Args:
            user_id: User identifier
            user_role: User role (if successful)
            session_id: Session identifier
            success: Whether authentication was successful
            method: Authentication method used
            ip_address: Client IP address
            user_agent: Client user agent
            metadata: Additional metadata
            
        Returns:
            Event ID for the logged authentication attempt
        """
        # Prepare metadata
        full_metadata = metadata or {}
        full_metadata.update({
            'success': success,
            'method': method,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Create audit event
        event = AuditEvent(
            event_id=f"auth_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role or UserRole.PATIENT,  # Default for failed attempts
            session_id=session_id,
            event_type=EventType.AUTHENTICATION,
            message=f"Authentication {'successful' if success else 'failed'} via {method}",
            metadata=full_metadata
        )
        
        # Log to database
        event_id = self.db.log_audit_event(event)
        
        # Log to appropriate logger
        if success:
            self.audit_logger.info(
                f"Authentication successful - User: {user_id}, Method: {method}, IP: {ip_address}"
            )
        else:
            self.security_logger.warning(
                f"Authentication failed - User: {user_id}, Method: {method}, IP: {ip_address}"
            )
        
        return event_id
    
    def log_authorization_decision(
        self,
        user_id: Optional[str],
        user_role: UserRole,
        session_id: Optional[str],
        resource: str,
        action: str,
        allowed: bool,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log authorization decisions for access control monitoring.
        
        Args:
            user_id: User identifier
            user_role: User role
            session_id: Session identifier
            resource: Resource being accessed
            action: Action being attempted
            allowed: Whether access was allowed
            reason: Reason for the decision
            metadata: Additional metadata
            
        Returns:
            Event ID for the logged authorization decision
        """
        # Prepare metadata
        full_metadata = metadata or {}
        full_metadata.update({
            'resource': resource,
            'action': action,
            'allowed': allowed,
            'reason': reason,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Create audit event
        event = AuditEvent(
            event_id=f"authz_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role,
            session_id=session_id,
            event_type=EventType.AUTHORIZATION,
            message=f"Access {'granted' if allowed else 'denied'} to {resource} for {action}",
            metadata=full_metadata
        )
        
        # Log to database
        event_id = self.db.log_audit_event(event)
        
        # Log to appropriate logger
        if allowed:
            self.audit_logger.info(
                f"Access granted - User: {user_id}, Role: {user_role.value}, "
                f"Resource: {resource}, Action: {action}"
            )
        else:
            self.security_logger.warning(
                f"Access denied - User: {user_id}, Role: {user_role.value}, "
                f"Resource: {resource}, Action: {action}, Reason: {reason}"
            )
        
        return event_id
    
    def log_cost_tracking(
        self,
        user_id: Optional[str],
        user_role: UserRole,
        session_id: Optional[str],
        cost_data: CostData,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log cost tracking information for usage monitoring and optimization.
        
        Args:
            user_id: User identifier
            user_role: User role
            session_id: Session identifier
            cost_data: Detailed cost information
            metadata: Additional metadata
            
        Returns:
            Event ID for the logged cost tracking
        """
        # Prepare metadata
        full_metadata = metadata or {}
        full_metadata.update({
            'model': cost_data.model,
            'input_tokens': cost_data.input_tokens,
            'output_tokens': cost_data.output_tokens,
            'total_tokens': cost_data.total_tokens,
            'cost_usd': cost_data.cost_usd,
            'cache_hit': cost_data.cache_hit,
            'timestamp': cost_data.timestamp.isoformat()
        })
        
        # Create audit event
        event = AuditEvent(
            event_id=f"cost_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role,
            session_id=session_id,
            event_type=EventType.COST_TRACKING,
            message=f"Cost tracking: ${cost_data.cost_usd:.4f} for {cost_data.total_tokens} tokens",
            cost_usd=cost_data.cost_usd,
            metadata=full_metadata
        )
        
        # Log to database
        event_id = self.db.log_audit_event(event)
        
        # Log to audit logger
        self.audit_logger.info(
            f"Cost tracked - User: {user_id}, Model: {cost_data.model}, "
            f"Cost: ${cost_data.cost_usd:.4f}, Tokens: {cost_data.total_tokens}"
        )
        
        return event_id
    
    def log_system_action(
        self,
        action: str,
        user_id: Optional[str] = None,
        user_role: Optional[UserRole] = None,
        session_id: Optional[str] = None,
        result: str = "success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log general system actions for operational monitoring.
        
        Args:
            action: Description of the system action
            user_id: User identifier (if applicable)
            user_role: User role (if applicable)
            session_id: Session identifier (if applicable)
            result: Result of the action
            metadata: Additional metadata
            
        Returns:
            Event ID for the logged system action
        """
        # Prepare metadata
        full_metadata = metadata or {}
        full_metadata.update({
            'action': action,
            'result': result,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Create audit event
        event = AuditEvent(
            event_id=f"system_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role or UserRole.ADMIN,  # Default to admin for system actions
            session_id=session_id,
            event_type=EventType.CHAT_REQUEST,  # Generic event type for system actions
            message=f"System action: {action} - {result}",
            metadata=full_metadata
        )
        
        # Log to database
        event_id = self.db.log_audit_event(event)
        
        # Log to audit logger
        self.audit_logger.info(f"System action logged - Action: {action}, Result: {result}")
        
        return event_id
    
    def _sanitize_content(self, content: str, max_length: int = 200) -> str:
        """
        Sanitize content for logging by truncating and removing sensitive patterns.
        
        Args:
            content: Content to sanitize
            max_length: Maximum length to keep
            
        Returns:
            Sanitized content safe for logging
        """
        # Truncate content
        sanitized = content[:max_length]
        
        # Remove potential PII patterns (basic sanitization)
        import re
        
        # Remove email patterns
        sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', sanitized)
        
        # Remove phone patterns
        sanitized = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', sanitized)
        
        # Remove SSN patterns
        sanitized = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', sanitized)
        
        # Add truncation indicator if needed
        if len(content) > max_length:
            sanitized += "... [TRUNCATED]"
        
        return sanitized
     
    @contextmanager
    def audit_context(
        self,
        user_id: Optional[str],
        user_role: UserRole,
        session_id: Optional[str],
        action: str
    ):
        """
        Context manager for auditing operations with automatic success/failure logging.
        
        Args:
            user_id: User identifier
            user_role: User role
            session_id: Session identifier
            action: Description of the action being performed
        """
        start_time = datetime.now(timezone.utc)
        event_id = None
        
        try:
            # Log start of action
            event_id = self.log_system_action(
                action=f"Started: {action}",
                user_id=user_id,
                user_role=user_role,
                session_id=session_id,
                result="started",
                metadata={'start_time': start_time.isoformat()}
            )
            
            yield event_id
            
            # Log successful completion
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            self.log_system_action(
                action=f"Completed: {action}",
                user_id=user_id,
                user_role=user_role,
                session_id=session_id,
                result="success",
                metadata={
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_ms': duration_ms,
                    'related_event_id': event_id
                }
            )
            
        except Exception as e:
            # Log failure
            end_time = datetime.now(timezone.utc)
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            self.log_system_action(
                action=f"Failed: {action}",
                user_id=user_id,
                user_role=user_role,
                session_id=session_id,
                result="error",
                metadata={
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_ms': duration_ms,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'related_event_id': event_id
                }
            )
            
            # Re-raise the exception
            raise
    
    def get_audit_summary(self, days: int = 1) -> Dict[str, Any]:
        """
        Get a summary of audit events for the specified number of days.
        
        Args:
            days: Number of days to include in summary
            
        Returns:
            Dictionary containing audit summary statistics
        """
        return self.db.get_metrics(days=days)
    
    def get_security_summary(self, days: int = 1) -> Dict[str, Any]:
        """
        Get a summary of security events for the specified number of days.
        
        Args:
            days: Number of days to include in summary
            
        Returns:
            Dictionary containing security summary statistics
        """
        from datetime import timedelta
        start_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        with self.db.get_connection() as conn:
            # Security events by threat type
            cursor = conn.execute("""
                SELECT threat_type, COUNT(*) as count, AVG(risk_score) as avg_risk
                FROM security_logs 
                WHERE timestamp >= ?
                GROUP BY threat_type
            """, (start_time,))
            
            threat_summary = {
                row['threat_type']: {
                    'count': row['count'],
                    'avg_risk_score': row['avg_risk']
                }
                for row in cursor.fetchall()
            }
            
            # Total security events
            cursor = conn.execute("""
                SELECT COUNT(*) as total_events, AVG(risk_score) as avg_risk
                FROM security_logs 
                WHERE timestamp >= ?
            """, (start_time,))
            
            totals = cursor.fetchone()
            
            return {
                'total_security_events': totals['total_events'],
                'average_risk_score': totals['avg_risk'] or 0.0,
                'events_by_threat_type': threat_summary,
                'period_days': days
            }


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def init_audit_logger(db_manager: Optional[DatabaseManager] = None) -> AuditLogger:
    """Initialize the audit logger with a specific database manager."""
    global _audit_logger
    _audit_logger = AuditLogger(db_manager)
    return _audit_logger