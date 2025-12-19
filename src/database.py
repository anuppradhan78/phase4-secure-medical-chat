"""
Database connection and schema management for the Secure Medical Chat system.
Handles SQLite database operations, migrations, and utilities.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

try:
    from .models import AuditEvent, SecurityEvent, UserSession, EventType, ThreatType, UserRole
except ImportError:
    # Handle case when running as script or in tests
    from models import AuditEvent, SecurityEvent, UserSession, EventType, ThreatType, UserRole

logger = logging.getLogger(__name__)


def serialize_metadata(metadata: Dict[str, Any]) -> str:
    """
    Serialize metadata dictionary to JSON, handling datetime objects.
    
    Args:
        metadata: Dictionary that may contain datetime objects
        
    Returns:
        JSON string with datetime objects converted to ISO format
    """
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
    
    return json.dumps(metadata, default=default_serializer)


class DatabaseManager:
    """Manages SQLite database connections and operations."""
    
    def __init__(self, db_path: str = "data/secure_chat.db"):
        """Initialize database manager with path to SQLite database."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database with required tables."""
        with self.get_connection() as conn:
            self._create_tables(conn)
            logger.info(f"Database initialized at {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
        finally:
            conn.close()
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create all required database tables."""
        
        # Audit logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                user_role TEXT NOT NULL,
                session_id TEXT,
                event_type TEXT NOT NULL,
                message TEXT,
                response TEXT,
                cost_usd REAL,
                latency_ms INTEGER,
                entities_redacted TEXT,  -- JSON array of entity types
                security_flags TEXT,     -- JSON array of security flags
                metadata TEXT,           -- JSON object for additional data
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Security logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE,
                timestamp TEXT NOT NULL,
                user_id TEXT,
                user_role TEXT,
                session_id TEXT,
                threat_type TEXT NOT NULL,
                blocked_content TEXT NOT NULL,
                risk_score REAL NOT NULL,
                detection_method TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                metadata TEXT,           -- JSON object for additional data
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # User sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE NOT NULL,
                user_id TEXT,
                user_role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_activity TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                request_count INTEGER DEFAULT 0,
                total_cost_usd REAL DEFAULT 0.0,
                metadata TEXT,           -- JSON object for additional data
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better query performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_role ON audit_logs(user_role)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_security_timestamp ON security_logs(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_security_threat_type ON security_logs(threat_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)")
        
        conn.commit()
        logger.info("Database tables created successfully")
    
    def log_audit_event(self, event: AuditEvent) -> str:
        """Log an audit event to the database."""
        event_id = event.event_id or f"audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO audit_logs 
                (event_id, timestamp, user_id, user_role, session_id, event_type, 
                 message, response, cost_usd, latency_ms, entities_redacted, 
                 security_flags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                event.timestamp.isoformat(),
                event.user_id,
                event.user_role.value,
                event.session_id,
                event.event_type.value,
                event.message,
                event.response,
                event.cost_usd,
                event.latency_ms,
                json.dumps([et.value for et in event.entities_redacted]),
                json.dumps(event.security_flags),
                serialize_metadata(event.metadata)
            ))
            conn.commit()
        
        logger.info(f"Audit event logged: {event_id}")
        return event_id
    
    def log_security_event(self, event: SecurityEvent) -> str:
        """Log a security event to the database."""
        event_id = event.event_id or f"security_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO security_logs 
                (event_id, timestamp, user_id, user_role, session_id, threat_type,
                 blocked_content, risk_score, detection_method, action_taken, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                event.timestamp.isoformat(),
                event.user_id,
                event.user_role.value if event.user_role else None,
                event.session_id,
                event.threat_type.value,
                event.blocked_content,
                event.risk_score,
                event.detection_method,
                event.action_taken,
                serialize_metadata(event.metadata)
            ))
            conn.commit()
        
        logger.info(f"Security event logged: {event_id}")
        return event_id
    
    def create_session(self, session: UserSession) -> str:
        """Create a new user session."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO user_sessions 
                (session_id, user_id, user_role, created_at, last_activity, 
                 expires_at, is_active, request_count, total_cost_usd, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.user_id,
                session.user_role.value,
                session.created_at.isoformat(),
                session.last_activity.isoformat(),
                session.expires_at.isoformat(),
                session.is_active,
                session.request_count,
                session.total_cost_usd,
                json.dumps(session.metadata)
            ))
            conn.commit()
        
        logger.info(f"Session created: {session.session_id}")
        return session.session_id
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Retrieve a user session by ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM user_sessions WHERE session_id = ? AND is_active = 1
            """, (session_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return UserSession(
                session_id=row['session_id'],
                user_id=row['user_id'],
                user_role=UserRole(row['user_role']),
                created_at=datetime.fromisoformat(row['created_at']),
                last_activity=datetime.fromisoformat(row['last_activity']),
                expires_at=datetime.fromisoformat(row['expires_at']),
                is_active=bool(row['is_active']),
                request_count=row['request_count'],
                total_cost_usd=row['total_cost_usd'],
                metadata=json.loads(row['metadata']) if row['metadata'] else {}
            )
    
    def update_session_activity(self, session_id: str, cost_increment: float = 0.0):
        """Update session last activity and increment request count and cost."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE user_sessions 
                SET last_activity = ?, 
                    request_count = request_count + 1,
                    total_cost_usd = total_cost_usd + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ? AND is_active = 1
            """, (
                datetime.utcnow().isoformat(),
                cost_increment,
                session_id
            ))
            conn.commit()
    
    def expire_session(self, session_id: str):
        """Mark a session as inactive."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE user_sessions 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))
            conn.commit()
        
        logger.info(f"Session expired: {session_id}")
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions from the database."""
        current_time = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                UPDATE user_sessions 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE expires_at < ? AND is_active = 1
            """, (current_time,))
            
            expired_count = cursor.rowcount
            conn.commit()
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired sessions")
        
        return expired_count
    
    def get_metrics(self, days: int = 1) -> Dict[str, Any]:
        """Get system metrics for the specified number of days."""
        start_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        with self.get_connection() as conn:
            # Total cost and query count
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as query_count,
                    COALESCE(SUM(cost_usd), 0) as total_cost,
                    COALESCE(AVG(latency_ms), 0) as avg_latency
                FROM audit_logs 
                WHERE timestamp >= ? AND event_type = 'chat_request'
            """, (start_time,))
            
            basic_metrics = cursor.fetchone()
            
            # Cost by user role
            cursor = conn.execute("""
                SELECT user_role, COALESCE(SUM(cost_usd), 0) as cost
                FROM audit_logs 
                WHERE timestamp >= ? AND event_type = 'chat_request' AND cost_usd IS NOT NULL
                GROUP BY user_role
            """, (start_time,))
            
            cost_by_role = {row['user_role']: row['cost'] for row in cursor.fetchall()}
            
            # Security events count
            cursor = conn.execute("""
                SELECT COUNT(*) as security_events
                FROM security_logs 
                WHERE timestamp >= ?
            """, (start_time,))
            
            security_count = cursor.fetchone()['security_events']
            
            return {
                'total_cost_usd': basic_metrics['total_cost'],
                'queries_today': basic_metrics['query_count'],
                'avg_latency_ms': basic_metrics['avg_latency'],
                'cost_by_role': cost_by_role,
                'security_events_today': security_count,
                'cache_hit_rate': 0.0,  # Will be calculated by cache service
                'cost_by_model': {}     # Will be populated by cost tracking service
            }
    
    def get_audit_logs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve audit logs with pagination."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM audit_logs 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_security_logs(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve security logs with pagination."""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM security_logs 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def reset_database(self):
        """Reset the database by dropping and recreating all tables."""
        with self.get_connection() as conn:
            # Drop existing tables
            conn.execute("DROP TABLE IF EXISTS audit_logs")
            conn.execute("DROP TABLE IF EXISTS security_logs")
            conn.execute("DROP TABLE IF EXISTS user_sessions")
            
            # Recreate tables
            self._create_tables(conn)
        
        logger.info("Database reset completed")
    
    def backup_database(self, backup_path: str):
        """Create a backup of the database."""
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self.get_connection() as source:
            with sqlite3.connect(str(backup_path)) as backup:
                source.backup(backup)
        
        logger.info(f"Database backed up to {backup_path}")


# Global database instance
_db_manager: Optional[DatabaseManager] = None


def get_database() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database(db_path: str = "data/secure_chat.db") -> DatabaseManager:
    """Initialize the database with a specific path."""
    global _db_manager
    _db_manager = DatabaseManager(db_path)
    return _db_manager


@contextmanager
def get_db_connection(db_path: str = "data/secure_chat.db"):
    """Simple database connection context manager for cost tracking."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()