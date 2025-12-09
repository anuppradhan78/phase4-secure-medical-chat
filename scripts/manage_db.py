#!/usr/bin/env python3
"""
Database management CLI script for the Secure Medical Chat system.
Provides commands for initializing, migrating, and maintaining the database.
"""

import sys
import argparse
import logging
from pathlib import Path

# Add src directory to path
src_path = str(Path(__file__).parent.parent / 'src')
sys.path.insert(0, src_path)

from db_utils import DatabaseUtils, init_database_for_app
from migrations import create_migration_manager
from models import UserRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_command(args):
    """Initialize the database."""
    success = init_database_for_app(args.db_path, force_reset=args.reset)
    if success:
        print("✅ Database initialized successfully")
        return 0
    else:
        print("❌ Database initialization failed")
        return 1


def migrate_command(args):
    """Run database migrations."""
    migration_manager = create_migration_manager(args.db_path)
    
    if args.down:
        # Migrate down
        rolled_back = migration_manager.migrate_down(args.version)
        if rolled_back:
            print(f"✅ Rolled back migrations: {rolled_back}")
        else:
            print("ℹ️  No migrations to roll back")
    else:
        # Migrate up
        applied = migration_manager.migrate_up(args.version)
        if applied:
            print(f"✅ Applied migrations: {applied}")
        else:
            print("ℹ️  Database is up to date")
    
    return 0


def status_command(args):
    """Show database status."""
    utils = DatabaseUtils(args.db_path)
    migration_manager = create_migration_manager(args.db_path)
    
    # Migration status
    migration_status = migration_manager.get_migration_status()
    print("📊 Database Status")
    print("=" * 50)
    print(f"Current Version: {migration_status['current_version']}")
    print(f"Target Version:  {migration_status['target_version']}")
    print(f"Needs Migration: {migration_status['needs_migration']}")
    print()
    
    # Database statistics
    stats = utils.get_database_stats()
    if 'error' not in stats:
        print("📈 Database Statistics")
        print("=" * 50)
        print(f"File Size:        {stats.get('file_size_bytes', 0):,} bytes")
        print(f"Audit Logs:       {stats.get('audit_logs_count', 0):,}")
        print(f"Security Logs:    {stats.get('security_logs_count', 0):,}")
        print(f"User Sessions:    {stats.get('user_sessions_count', 0):,}")
        print(f"Active Sessions:  {stats.get('active_sessions', 0):,}")
        print(f"Recent Audits:    {stats.get('recent_audit_events', 0):,}")
        print(f"Recent Security:  {stats.get('recent_security_events', 0):,}")
    else:
        print(f"❌ Error getting stats: {stats['error']}")
    
    return 0


def cleanup_command(args):
    """Clean up old database data."""
    utils = DatabaseUtils(args.db_path)
    
    print(f"🧹 Cleaning up data older than {args.days} days...")
    cleanup_stats = utils.cleanup_old_data(args.days)
    
    if 'error' not in cleanup_stats:
        print("✅ Cleanup completed:")
        for key, value in cleanup_stats.items():
            print(f"  {key}: {value}")
    else:
        print(f"❌ Cleanup failed: {cleanup_stats['error']}")
        return 1
    
    if args.vacuum:
        print("🔧 Vacuuming database...")
        if utils.vacuum_database():
            print("✅ Database vacuum completed")
        else:
            print("❌ Database vacuum failed")
            return 1
    
    return 0


def test_session_command(args):
    """Create a test session."""
    utils = DatabaseUtils(args.db_path)
    
    try:
        role = UserRole(args.role)
        session_id = utils.create_test_session(role)
        print(f"✅ Created test session: {session_id}")
        print(f"   Role: {role.value}")
        return 0
    except ValueError:
        print(f"❌ Invalid role: {args.role}")
        print(f"   Valid roles: {[r.value for r in UserRole]}")
        return 1


def export_command(args):
    """Export database data."""
    utils = DatabaseUtils(args.db_path)
    
    print(f"📤 Exporting data to {args.output_dir}...")
    exported_files = utils.export_data(args.output_dir, args.format)
    
    if 'error' not in exported_files:
        print("✅ Export completed:")
        for table, file_path in exported_files.items():
            print(f"  {table}: {file_path}")
    else:
        print(f"❌ Export failed: {exported_files['error']}")
        return 1
    
    return 0


def verify_command(args):
    """Verify database integrity."""
    utils = DatabaseUtils(args.db_path)
    
    print("🔍 Verifying database integrity...")
    if utils.verify_database_integrity():
        print("✅ Database integrity check passed")
        return 0
    else:
        print("❌ Database integrity check failed")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Database management for Secure Medical Chat",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--db-path',
        default='data/secure_chat.db',
        help='Path to SQLite database file (default: data/secure_chat.db)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize database')
    init_parser.add_argument('--reset', action='store_true', help='Reset database before initialization')
    init_parser.set_defaults(func=init_command)
    
    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Run database migrations')
    migrate_parser.add_argument('--version', type=int, help='Target migration version')
    migrate_parser.add_argument('--down', action='store_true', help='Migrate down instead of up')
    migrate_parser.set_defaults(func=migrate_command)
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show database status')
    status_parser.set_defaults(func=status_command)
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old data')
    cleanup_parser.add_argument('--days', type=int, default=30, help='Days of data to keep (default: 30)')
    cleanup_parser.add_argument('--vacuum', action='store_true', help='Vacuum database after cleanup')
    cleanup_parser.set_defaults(func=cleanup_command)
    
    # Test session command
    test_parser = subparsers.add_parser('test-session', help='Create test session')
    test_parser.add_argument('--role', default='patient', choices=['patient', 'physician', 'admin'],
                           help='User role for test session (default: patient)')
    test_parser.set_defaults(func=test_session_command)
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export database data')
    export_parser.add_argument('output_dir', help='Output directory for exported files')
    export_parser.add_argument('--format', choices=['json', 'csv'], default='json',
                             help='Export format (default: json)')
    export_parser.set_defaults(func=export_command)
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify database integrity')
    verify_parser.set_defaults(func=verify_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except Exception as e:
        logger.error(f"Command failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())