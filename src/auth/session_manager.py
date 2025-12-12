"""
Session management for user authentication and tracking.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
from ..models import UserSession, UserRole


class SessionManager:
    """Manages user sessions with expiration and tracking."""
    
    def __init__(self, default_session_hours: int = 24):
        self.sessions: Dict[str, UserSession] = {}
        self.user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        self.default_session_hours = default_session_hours
    
    def create_session(
        self, 
        user_id: str, 
        user_role: UserRole, 
        session_duration_hours: Optional[int] = None
    ) -> UserSession:
        """
        Create a new user session.
        
        Args:
            user_id: User identifier
            user_role: User's role
            session_duration_hours: Custom session duration (defaults to 24 hours)
            
        Returns:
            UserSession object
        """
        session_id = str(uuid.uuid4())
        duration_hours = session_duration_hours or self.default_session_hours
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=duration_hours)
        
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            user_role=user_role,
            created_at=now,
            last_activity=now,
            expires_at=expires_at,
            is_active=True,
            request_count=0,
            total_cost_usd=0.0,
            metadata={}
        )
        
        # Store session
        self.sessions[session_id] = session
        
        # Track user sessions
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        self.user_sessions[user_id].append(session_id)
        
        return session
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            UserSession object or None if not found/expired/inactive
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # Check if session is expired or inactive
        if self._is_session_expired(session) or not session.is_active:
            self._deactivate_session(session_id)
            return None
        
        return session
    
    def validate_session(self, session_id: str) -> Optional[UserSession]:
        """
        Validate and update session activity.
        
        Args:
            session_id: Session identifier
            
        Returns:
            UserSession object or None if invalid/expired
        """
        session = self.get_session(session_id)
        if not session or not session.is_active:
            return None
        
        # Update last activity
        session.last_activity = datetime.now(timezone.utc)
        return session
    
    def update_session_activity(
        self, 
        session_id: str, 
        cost: float = 0.0, 
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Update session with new activity.
        
        Args:
            session_id: Session identifier
            cost: Cost to add to session total
            metadata: Additional metadata to merge
            
        Returns:
            True if updated successfully, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        # Update activity
        session.last_activity = datetime.now(timezone.utc)
        session.request_count += 1
        session.total_cost_usd += cost
        
        # Merge metadata
        if metadata:
            session.metadata.update(metadata)
        
        return True
    
    def deactivate_session(self, session_id: str) -> bool:
        """
        Manually deactivate a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deactivated, False if not found
        """
        return self._deactivate_session(session_id)
    
    def _deactivate_session(self, session_id: str) -> bool:
        """Internal method to deactivate a session."""
        session = self.sessions.get(session_id)
        if session:
            session.is_active = False
            return True
        return False
    
    def _is_session_expired(self, session: UserSession) -> bool:
        """Check if a session is expired."""
        return datetime.now(timezone.utc) > session.expires_at
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions from memory.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if self._is_session_expired(session):
                expired_sessions.append(session_id)
        
        # Remove expired sessions
        for session_id in expired_sessions:
            self._remove_session(session_id)
        
        return len(expired_sessions)
    
    def _remove_session(self, session_id: str):
        """Remove a session completely."""
        session = self.sessions.get(session_id)
        if session and session.user_id:
            # Remove from user sessions tracking
            if session.user_id in self.user_sessions:
                try:
                    self.user_sessions[session.user_id].remove(session_id)
                    if not self.user_sessions[session.user_id]:
                        del self.user_sessions[session.user_id]
                except ValueError:
                    pass  # Session ID not in list
        
        # Remove from main sessions dict
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_user_sessions(self, user_id: str) -> List[UserSession]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of active UserSession objects
        """
        session_ids = self.user_sessions.get(user_id, [])
        active_sessions = []
        
        for session_id in session_ids.copy():  # Copy to avoid modification during iteration
            session = self.get_session(session_id)
            if session and session.is_active:
                active_sessions.append(session)
            else:
                # Clean up invalid session reference
                try:
                    self.user_sessions[user_id].remove(session_id)
                except ValueError:
                    pass
        
        return active_sessions
    
    def revoke_user_sessions(self, user_id: str) -> int:
        """
        Revoke all sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions revoked
        """
        session_ids = self.user_sessions.get(user_id, []).copy()
        revoked_count = 0
        
        for session_id in session_ids:
            if self._deactivate_session(session_id):
                revoked_count += 1
        
        return revoked_count
    
    def extend_session(self, session_id: str, additional_hours: int) -> bool:
        """
        Extend a session's expiration time.
        
        Args:
            session_id: Session identifier
            additional_hours: Hours to add to expiration
            
        Returns:
            True if extended, False if session not found
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.expires_at += timedelta(hours=additional_hours)
        return True
    
    def get_session_stats(self) -> Dict[str, any]:
        """Get statistics about current sessions."""
        total_sessions = len(self.sessions)
        active_sessions = sum(1 for s in self.sessions.values() if s.is_active)
        expired_sessions = sum(1 for s in self.sessions.values() if self._is_session_expired(s))
        
        # Role distribution
        role_counts = {}
        for session in self.sessions.values():
            if session.is_active and not self._is_session_expired(session):
                role = session.user_role.value
                role_counts[role] = role_counts.get(role, 0) + 1
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "sessions_by_role": role_counts,
            "unique_users": len(self.user_sessions)
        }
    
    def create_demo_session(self, user_role: UserRole) -> UserSession:
        """
        Create a demo session for testing.
        
        Args:
            user_role: Role for the demo session
            
        Returns:
            UserSession object
        """
        demo_user_id = f"demo_{user_role.value}_{uuid.uuid4().hex[:8]}"
        return self.create_session(demo_user_id, user_role)