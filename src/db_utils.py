"""
Database utilities for initialization, cleanup, and maintenance.
Provides helper functions for database operations and management.
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from database import DatabaseManager, get_database
from migrations import MigrationManager, create_migration_manager
from models import UserSession, UserRole

logger = logging.getLogger(__name__)


class DatabaseUtils:
    """Utility class for database operations and maintenance."""
    
    def __init__(self, db_path: str = "data/secure_chat.db"):
        self.db_path = Path(db_path)
        self.db_manager = DatabaseManager(str(db_path))
        self.migration_manager = create_migration_manager(str(db_path))
    
    def initialize_database(self, force_reset: bool = False) -> bool:
        """
        Initialize the database with proper schema and migrations.
        
        Args:
            force_reset: If True, reset the database before initialization
            
        Returns:
            True if initialization was successful
        """
        try:
            if force_reset:
                logger.info("Force reset requested - dropping existing database")
                self.reset_database()
            
            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Run migrations to ensure schema is up to date
            logger.info("Running database migrations...")
            applied_migrations = self.migration_manager.migrate_up()
            
            if applied_migrations:
                logger.info(f"Applied migrations: {applied_migrations}")
            else:
                logger.info("Database schema is up to date")
            
            # Verify database integrity
            if self.verify_database_integrity():
                logger.info("Database initialization completed successfully")
                return True
            else:
                logger.error("Database integrity check failed")
                return False
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    def reset_database(self) -> bool:
        """
        Reset the database by removing the file and recreating it.
        
        Returns:
            True if reset was successful
        """
        try:
            if self.db_path.exists():
                self.db_path.unlink()
                logger.info(f"Removed existing database: {self.db_path}")
            
            # Recreate database manager to initialize fresh database
            self.db_manager = DatabaseManager(str(self.db_path))
            logger.info("Database reset completed")
            return True
            
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            return False
    
    def verify_database_integrity(self) -> bool:
        """
        Verify database integrity by checking table structure and constraints.
        
        Returns:
            True if database integrity is valid
        """
        try:
            with self.db_manager.get_connection() as conn:
                # Check if all required tables exist
                required_tables = ['audit_logs', 'security_logs', 'user_sessions']
                
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """)
                
                existing_tables = {row[0] for row in cursor.fetchall()}
                missing_tables = set(required_tables) - existing_tables
                
                if missing_tables:
                    logger.error(f"Missing required tables: {missing_tables}")
                    return False
                
                # Check table schemas
                for table in required_tables:
                    cursor = conn.execute(f"PRAGMA table_info({table})")
                    columns = cursor.fetchall()
                    
                    if not columns:
                        logger.error(f"Table {table} has no columns")
                        return False
                
                # Run integrity check
                cursor = conn.execute("PRAGMA integrity_check")
                integrity_result = cursor.fetchone()[0]
                
                if integrity_result != "ok":
                    logger.error(f"Database integrity check failed: {integrity_result}")
                    return False
                
                logger.info("Database integrity verification passed")
                return True
                
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> Dict[str, int]:
        """
        Clean up old data from the database.
        
        Args:
            days_to_keep: Number of days of data to retain
            
        Returns:
            Dictionary with cleanup statistics
        """
        cutoff_date = (datetime.utcnow() - timedelta(days=days_to_keep)).isoformat()
        cleanup_stats = {}
        
        try:
            with self.db_manager.get_connection() as conn:
                # Clean up old audit logs
                cursor = conn.execute("""
                    DELETE FROM audit_logs WHERE timestamp < ?
                """, (cutoff_date,))
                cleanup_stats['audit_logs_deleted'] = cursor.rowcount
                
                # Clean up old security logs
                cursor = conn.execute("""
                    DELETE FROM security_logs WHERE timestamp < ?
                """, (cutoff_date,))
                cleanup_stats['security_logs_deleted'] = cursor.rowcount
                
                # Clean up expired sessions
                expired_sessions = self.db_manager.cleanup_expired_sessions()
                cleanup_stats['expired_sessions'] = expired_sessions
                
                conn.commit()
                
                logger.info(f"Data cleanup completed: {cleanup_stats}")
                return cleanup_stats
                
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
            return {'error': str(e)}
    
    def vacuum_database(self) -> bool:
        """
        Vacuum the database to reclaim space and optimize performance.
        
        Returns:
            True if vacuum was successful
        """
        try:
            with self.db_manager.get_connection() as conn:
                # Get database size before vacuum
                cursor = conn.execute("PRAGMA page_count")
                pages_before = cursor.fetchone()[0]
                
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                
                size_before = pages_before * page_size
                
                # Perform vacuum
                conn.execute("VACUUM")
                
                # Get database size after vacuum
                cursor = conn.execute("PRAGMA page_count")
                pages_after = cursor.fetchone()[0]
                
                size_after = pages_after * page_size
                space_saved = size_before - size_after
                
                logger.info(f"Database vacuum completed. Space saved: {space_saved} bytes")
                return True
                
        except Exception as e:
            logger.error(f"Database vacuum failed: {e}")
            return False
    
    def create_test_session(self, user_role: UserRole = UserRole.PATIENT) -> str:
        """
        Create a test user session for development/testing purposes.
        
        Args:
            user_role: Role for the test user
            
        Returns:
            Session ID of the created session
        """
        session_id = f"test_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        session = UserSession(
            session_id=session_id,
            user_id=f"test_user_{user_role.value}",
            user_role=user_role,
            created_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_active=True,
            request_count=0,
            total_cost_usd=0.0,
            metadata={"test_session": True, "created_by": "db_utils"}
        )
        
        self.db_manager.create_session(session)
        logger.info(f"Created test session: {session_id} for role: {user_role.value}")
        return session_id
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive database statistics.
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with self.db_manager.get_connection() as conn:
                stats = {}
                
                # Database file size
                if self.db_path.exists():
                    stats['file_size_bytes'] = self.db_path.stat().st_size
                else:
                    stats['file_size_bytes'] = 0
                
                # Table row counts
                tables = ['audit_logs', 'security_logs', 'user_sessions']
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f'{table}_count'] = cursor.fetchone()[0]
                
                # Active sessions count
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM user_sessions WHERE is_active = 1
                """)
                stats['active_sessions'] = cursor.fetchone()[0]
                
                # Recent activity (last 24 hours)
                recent_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
                
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM audit_logs WHERE timestamp >= ?
                """, (recent_time,))
                stats['recent_audit_events'] = cursor.fetchone()[0]
                
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM security_logs WHERE timestamp >= ?
                """, (recent_time,))
                stats['recent_security_events'] = cursor.fetchone()[0]
                
                # Migration status
                migration_status = self.migration_manager.get_migration_status()
                stats['schema_version'] = migration_status['current_version']
                stats['needs_migration'] = migration_status['needs_migration']
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {'error': str(e)}
    
    def export_data(self, output_dir: str, format: str = 'json') -> Dict[str, str]:
        """
        Export database data to files.
        
        Args:
            output_dir: Directory to save exported files
            format: Export format ('json' or 'csv')
            
        Returns:
            Dictionary with paths to exported files
        """
        import json
        import csv
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        exported_files = {}
        
        try:
            # Export audit logs
            audit_logs = self.db_manager.get_audit_logs(limit=10000)
            if format == 'json':
                audit_file = output_path / 'audit_logs.json'
                with open(audit_file, 'w') as f:
                    json.dump(audit_logs, f, indent=2, default=str)
            else:  # CSV
                audit_file = output_path / 'audit_logs.csv'
                if audit_logs:
                    with open(audit_file, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=audit_logs[0].keys())
                        writer.writeheader()
                        writer.writerows(audit_logs)
            
            exported_files['audit_logs'] = str(audit_file)
            
            # Export security logs
            security_logs = self.db_manager.get_security_logs(limit=10000)
            if format == 'json':
                security_file = output_path / 'security_logs.json'
                with open(security_file, 'w') as f:
                    json.dump(security_logs, f, indent=2, default=str)
            else:  # CSV
                security_file = output_path / 'security_logs.csv'
                if security_logs:
                    with open(security_file, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=security_logs[0].keys())
                        writer.writeheader()
                        writer.writerows(security_logs)
            
            exported_files['security_logs'] = str(security_file)
            
            logger.info(f"Data exported to {output_dir}")
            return exported_files
            
        except Exception as e:
            logger.error(f"Data export failed: {e}")
            return {'error': str(e)}


def init_database_for_app(db_path: str = None, force_reset: bool = False) -> bool:
    """
    Initialize database for the application.
    
    Args:
        db_path: Path to database file (uses default if None)
        force_reset: Whether to reset database before initialization
        
    Returns:
        True if initialization was successful
    """
    if db_path is None:
        db_path = os.getenv('DATABASE_PATH', 'data/secure_chat.db')
    
    utils = DatabaseUtils(db_path)
    return utils.initialize_database(force_reset=force_reset)


def cleanup_database(days_to_keep: int = 30) -> Dict[str, int]:
    """
    Clean up old data from the database.
    
    Args:
        days_to_keep: Number of days of data to retain
        
    Returns:
        Dictionary with cleanup statistics
    """
    db = get_database()
    utils = DatabaseUtils(db.db_path)
    return utils.cleanup_old_data(days_to_keep)


def get_db_stats() -> Dict[str, Any]:
    """Get database statistics."""
    db = get_database()
    utils = DatabaseUtils(db.db_path)
    return utils.get_database_stats()