"""
Database migration scripts for the Secure Medical Chat system.
Handles database schema versioning and upgrades.
"""

import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Callable, Dict

logger = logging.getLogger(__name__)


class Migration:
    """Represents a single database migration."""
    
    def __init__(self, version: int, description: str, up_func: Callable, down_func: Callable = None):
        self.version = version
        self.description = description
        self.up_func = up_func
        self.down_func = down_func
    
    def apply(self, conn: sqlite3.Connection):
        """Apply the migration."""
        logger.info(f"Applying migration {self.version}: {self.description}")
        self.up_func(conn)
    
    def rollback(self, conn: sqlite3.Connection):
        """Rollback the migration."""
        if self.down_func:
            logger.info(f"Rolling back migration {self.version}: {self.description}")
            self.down_func(conn)
        else:
            raise ValueError(f"No rollback function defined for migration {self.version}")


class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.migrations: List[Migration] = []
        self._register_migrations()
    
    def _register_migrations(self):
        """Register all available migrations."""
        
        # Migration 1: Initial schema
        def migration_001_up(conn: sqlite3.Connection):
            """Create initial database schema."""
            # Create migration tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
            """)
            
            # Create audit logs table
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
                    entities_redacted TEXT,
                    security_flags TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create security logs table
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
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create user sessions table
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
                    metadata TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
        
        def migration_001_down(conn: sqlite3.Connection):
            """Drop initial schema."""
            conn.execute("DROP TABLE IF EXISTS audit_logs")
            conn.execute("DROP TABLE IF EXISTS security_logs")
            conn.execute("DROP TABLE IF EXISTS user_sessions")
            conn.execute("DROP TABLE IF EXISTS schema_migrations")
            conn.commit()
        
        self.migrations.append(Migration(
            version=1,
            description="Initial database schema",
            up_func=migration_001_up,
            down_func=migration_001_down
        ))
        
        # Migration 2: Add indexes for performance
        def migration_002_up(conn: sqlite3.Connection):
            """Add database indexes for better query performance."""
            # Audit logs indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_role ON audit_logs(user_role)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_id)")
            
            # Security logs indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_security_timestamp ON security_logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_security_threat_type ON security_logs(threat_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_security_user ON security_logs(user_id)")
            
            # User sessions indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)")
            
            conn.commit()
        
        def migration_002_down(conn: sqlite3.Connection):
            """Remove performance indexes."""
            conn.execute("DROP INDEX IF EXISTS idx_audit_timestamp")
            conn.execute("DROP INDEX IF EXISTS idx_audit_user_role")
            conn.execute("DROP INDEX IF EXISTS idx_audit_event_type")
            conn.execute("DROP INDEX IF EXISTS idx_audit_session")
            conn.execute("DROP INDEX IF EXISTS idx_security_timestamp")
            conn.execute("DROP INDEX IF EXISTS idx_security_threat_type")
            conn.execute("DROP INDEX IF EXISTS idx_security_user")
            conn.execute("DROP INDEX IF EXISTS idx_sessions_active")
            conn.execute("DROP INDEX IF EXISTS idx_sessions_expires")
            conn.execute("DROP INDEX IF EXISTS idx_sessions_user")
            conn.commit()
        
        self.migrations.append(Migration(
            version=2,
            description="Add database indexes for performance",
            up_func=migration_002_up,
            down_func=migration_002_down
        ))
    
    def get_current_version(self) -> int:
        """Get the current database schema version."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("""
                    SELECT MAX(version) as version 
                    FROM schema_migrations
                """)
                result = cursor.fetchone()
                return result[0] if result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table doesn't exist, database is at version 0
            return 0
    
    def get_target_version(self) -> int:
        """Get the latest available migration version."""
        return max(m.version for m in self.migrations) if self.migrations else 0
    
    def migrate_up(self, target_version: int = None) -> List[int]:
        """Apply migrations up to the target version."""
        if target_version is None:
            target_version = self.get_target_version()
        
        current_version = self.get_current_version()
        applied_migrations = []
        
        if current_version >= target_version:
            logger.info(f"Database is already at version {current_version}")
            return applied_migrations
        
        with sqlite3.connect(str(self.db_path)) as conn:
            # Ensure migration tracking table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
            """)
            
            # Apply migrations in order
            for migration in sorted(self.migrations, key=lambda m: m.version):
                if migration.version > current_version and migration.version <= target_version:
                    try:
                        migration.apply(conn)
                        
                        # Record the migration
                        conn.execute("""
                            INSERT OR REPLACE INTO schema_migrations 
                            (version, description, applied_at)
                            VALUES (?, ?, ?)
                        """, (
                            migration.version,
                            migration.description,
                            datetime.utcnow().isoformat()
                        ))
                        
                        applied_migrations.append(migration.version)
                        logger.info(f"Applied migration {migration.version}")
                        
                    except Exception as e:
                        logger.error(f"Failed to apply migration {migration.version}: {e}")
                        conn.rollback()
                        raise
            
            conn.commit()
        
        logger.info(f"Database migrated from version {current_version} to {target_version}")
        return applied_migrations
    
    def migrate_down(self, target_version: int) -> List[int]:
        """Rollback migrations down to the target version."""
        current_version = self.get_current_version()
        rolled_back_migrations = []
        
        if current_version <= target_version:
            logger.info(f"Database is already at or below version {target_version}")
            return rolled_back_migrations
        
        with sqlite3.connect(str(self.db_path)) as conn:
            # Rollback migrations in reverse order
            for migration in sorted(self.migrations, key=lambda m: m.version, reverse=True):
                if migration.version > target_version and migration.version <= current_version:
                    try:
                        migration.rollback(conn)
                        
                        # Remove the migration record
                        conn.execute("""
                            DELETE FROM schema_migrations 
                            WHERE version = ?
                        """, (migration.version,))
                        
                        rolled_back_migrations.append(migration.version)
                        logger.info(f"Rolled back migration {migration.version}")
                        
                    except Exception as e:
                        logger.error(f"Failed to rollback migration {migration.version}: {e}")
                        conn.rollback()
                        raise
            
            conn.commit()
        
        logger.info(f"Database rolled back from version {current_version} to {target_version}")
        return rolled_back_migrations
    
    def get_migration_status(self) -> Dict[str, any]:
        """Get the current migration status."""
        current_version = self.get_current_version()
        target_version = self.get_target_version()
        
        with sqlite3.connect(str(self.db_path)) as conn:
            try:
                cursor = conn.execute("""
                    SELECT version, description, applied_at 
                    FROM schema_migrations 
                    ORDER BY version
                """)
                applied_migrations = [
                    {
                        'version': row[0],
                        'description': row[1],
                        'applied_at': row[2]
                    }
                    for row in cursor.fetchall()
                ]
            except sqlite3.OperationalError:
                applied_migrations = []
        
        return {
            'current_version': current_version,
            'target_version': target_version,
            'needs_migration': current_version < target_version,
            'applied_migrations': applied_migrations,
            'available_migrations': [
                {
                    'version': m.version,
                    'description': m.description
                }
                for m in self.migrations
            ]
        }


def create_migration_manager(db_path: str = "data/secure_chat.db") -> MigrationManager:
    """Create a migration manager for the specified database."""
    return MigrationManager(db_path)