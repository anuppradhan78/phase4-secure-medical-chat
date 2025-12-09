"""
Tests for database functionality.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database import DatabaseManager
from db_utils import DatabaseUtils
from migrations import create_migration_manager
from models import (
    AuditEvent, SecurityEvent, UserSession, UserRole, 
    EventType, ThreatType, EntityType
)


class TestDatabaseManager:
    """Test database manager functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_database_initialization(self, temp_db):
        """Test database initialization creates required tables."""
        db_manager = DatabaseManager(temp_db)
        
        # Check that database file was created
        assert Path(temp_db).exists()
        
        # Check that tables were created
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = {row[0] for row in cursor.fetchall()}
            
            required_tables = {'audit_logs', 'security_logs', 'user_sessions'}
            assert required_tables.issubset(tables)
    
    def test_audit_event_logging(self, temp_db):
        """Test logging audit events."""
        db_manager = DatabaseManager(temp_db)
        
        # Create test audit event
        event = AuditEvent(
            user_id="test_user",
            user_role=UserRole.PATIENT,
            session_id="test_session",
            event_type=EventType.CHAT_REQUEST,
            message="Test message",
            response="Test response",
            cost_usd=0.01,
            latency_ms=500,
            entities_redacted=[EntityType.PERSON],
            security_flags=["test_flag"]
        )
        
        # Log the event
        event_id = db_manager.log_audit_event(event)
        assert event_id is not None
        
        # Verify event was logged
        logs = db_manager.get_audit_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]['user_id'] == "test_user"
        assert logs[0]['event_type'] == EventType.CHAT_REQUEST.value
    
    def test_security_event_logging(self, temp_db):
        """Test logging security events."""
        db_manager = DatabaseManager(temp_db)
        
        # Create test security event
        event = SecurityEvent(
            user_id="test_user",
            user_role=UserRole.PATIENT,
            threat_type=ThreatType.PROMPT_INJECTION,
            blocked_content="Malicious prompt",
            risk_score=0.8,
            detection_method="pattern_matching",
            action_taken="blocked"
        )
        
        # Log the event
        event_id = db_manager.log_security_event(event)
        assert event_id is not None
        
        # Verify event was logged
        logs = db_manager.get_security_logs(limit=1)
        assert len(logs) == 1
        assert logs[0]['threat_type'] == ThreatType.PROMPT_INJECTION.value
        assert logs[0]['risk_score'] == 0.8
    
    def test_session_management(self, temp_db):
        """Test user session management."""
        db_manager = DatabaseManager(temp_db)
        
        # Create test session
        session = UserSession(
            session_id="test_session_123",
            user_id="test_user",
            user_role=UserRole.PHYSICIAN,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_active=True
        )
        
        # Create session
        session_id = db_manager.create_session(session)
        assert session_id == "test_session_123"
        
        # Retrieve session
        retrieved_session = db_manager.get_session("test_session_123")
        assert retrieved_session is not None
        assert retrieved_session.user_role == UserRole.PHYSICIAN
        assert retrieved_session.is_active is True
        
        # Update session activity
        db_manager.update_session_activity("test_session_123", cost_increment=0.05)
        
        updated_session = db_manager.get_session("test_session_123")
        assert updated_session.request_count == 1
        assert updated_session.total_cost_usd == 0.05
        
        # Expire session
        db_manager.expire_session("test_session_123")
        expired_session = db_manager.get_session("test_session_123")
        assert expired_session is None  # Should not return inactive sessions
    
    def test_metrics_calculation(self, temp_db):
        """Test metrics calculation."""
        db_manager = DatabaseManager(temp_db)
        
        # Create some test data
        for i in range(3):
            event = AuditEvent(
                user_id=f"user_{i}",
                user_role=UserRole.PATIENT if i % 2 == 0 else UserRole.PHYSICIAN,
                event_type=EventType.CHAT_REQUEST,
                cost_usd=0.01 * (i + 1),
                latency_ms=100 * (i + 1)
            )
            db_manager.log_audit_event(event)
        
        # Get metrics
        metrics = db_manager.get_metrics(days=1)
        
        assert metrics['queries_today'] == 3
        assert metrics['total_cost_usd'] == 0.06  # 0.01 + 0.02 + 0.03
        assert metrics['avg_latency_ms'] == 200.0  # (100 + 200 + 300) / 3


class TestDatabaseUtils:
    """Test database utilities."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_database_initialization(self, temp_db):
        """Test database initialization utility."""
        utils = DatabaseUtils(temp_db)
        
        # Initialize database
        success = utils.initialize_database()
        assert success is True
        
        # Verify integrity
        integrity_ok = utils.verify_database_integrity()
        assert integrity_ok is True
    
    def test_database_reset(self, temp_db):
        """Test database reset functionality."""
        utils = DatabaseUtils(temp_db)
        
        # Initialize and add some data
        utils.initialize_database()
        db_manager = DatabaseManager(temp_db)
        
        event = AuditEvent(
            user_role=UserRole.PATIENT,
            event_type=EventType.CHAT_REQUEST
        )
        db_manager.log_audit_event(event)
        
        # Verify data exists
        logs = db_manager.get_audit_logs()
        assert len(logs) == 1
        
        # Reset database
        success = utils.reset_database()
        assert success is True
        
        # Verify data is gone
        new_db_manager = DatabaseManager(temp_db)
        logs = new_db_manager.get_audit_logs()
        assert len(logs) == 0
    
    def test_create_test_session(self, temp_db):
        """Test creating test sessions."""
        utils = DatabaseUtils(temp_db)
        utils.initialize_database()
        
        # Create test session
        session_id = utils.create_test_session(UserRole.PHYSICIAN)
        assert session_id is not None
        assert "test_session" in session_id
        
        # Verify session was created
        db_manager = DatabaseManager(temp_db)
        session = db_manager.get_session(session_id)
        assert session is not None
        assert session.user_role == UserRole.PHYSICIAN
        assert session.metadata.get("test_session") is True


class TestMigrations:
    """Test database migrations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_migration_manager(self, temp_db):
        """Test migration manager functionality."""
        migration_manager = create_migration_manager(temp_db)
        
        # Check initial version
        current_version = migration_manager.get_current_version()
        assert current_version == 0
        
        # Apply migrations
        applied = migration_manager.migrate_up()
        assert len(applied) > 0
        
        # Check version after migration
        new_version = migration_manager.get_current_version()
        assert new_version > 0
        
        # Check migration status
        status = migration_manager.get_migration_status()
        assert status['current_version'] == new_version
        assert status['needs_migration'] is False
    
    def test_migration_rollback(self, temp_db):
        """Test migration rollback functionality."""
        migration_manager = create_migration_manager(temp_db)
        
        # Apply all migrations
        migration_manager.migrate_up()
        current_version = migration_manager.get_current_version()
        
        # Rollback to version 1
        rolled_back = migration_manager.migrate_down(1)
        assert len(rolled_back) > 0
        
        # Check version after rollback
        new_version = migration_manager.get_current_version()
        assert new_version == 1
        assert new_version < current_version


if __name__ == '__main__':
    pytest.main([__file__])