"""
Cost tracking service for persistent storage and advanced analytics.

This module provides:
- Persistent cost data storage in SQLite
- Advanced cost analytics and reporting
- Cost optimization recommendations
- Budget monitoring and alerts
"""

import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

try:
    from ..models import CostData, UserRole
    from ..database import get_db_connection
except ImportError:
    # Handle case when running as script or in tests
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from models import CostData, UserRole
    from database import get_db_connection


logger = logging.getLogger(__name__)


class CostTracker:
    """
    Persistent cost tracking service with advanced analytics.
    
    This service provides:
    - Persistent storage of cost data
    - Advanced cost analytics and reporting
    - Cost optimization recommendations
    - Budget monitoring and alerts
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize cost tracker with database connection."""
        self.db_path = db_path or "data/secure_chat.db"
        self._ensure_tables_exist()
    
    def _ensure_tables_exist(self):
        """Ensure cost tracking tables exist in the database."""
        with get_db_connection(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cost_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    user_role TEXT NOT NULL,
                    session_id TEXT,
                    cache_hit BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cost_timestamp 
                ON cost_tracking(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cost_user_role 
                ON cost_tracking(user_role)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cost_model 
                ON cost_tracking(model)
            """)
            
            conn.commit()
            logger.info("Cost tracking tables initialized")
    
    def record_cost(self, cost_data: CostData) -> int:
        """
        Record cost data in the database.
        
        Args:
            cost_data: CostData object to store
            
        Returns:
            ID of the inserted record
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO cost_tracking 
                (timestamp, model, input_tokens, output_tokens, total_tokens, 
                 cost_usd, user_role, session_id, cache_hit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cost_data.timestamp.isoformat(),
                cost_data.model,
                cost_data.input_tokens,
                cost_data.output_tokens,
                cost_data.total_tokens,
                cost_data.cost_usd,
                cost_data.user_role.value,
                cost_data.session_id,
                cost_data.cache_hit
            ))
            
            conn.commit()
            record_id = cursor.lastrowid
            
            logger.info(
                f"Recorded cost: ID={record_id}, Model={cost_data.model}, "
                f"Cost=${cost_data.cost_usd:.4f}, Role={cost_data.user_role.value}"
            )
            
            return record_id
    
    def get_cost_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_role: Optional[UserRole] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive cost summary with analytics.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
            user_role: Optional user role filter
            
        Returns:
            Dict with detailed cost summary
        """
        # Default to last 24 hours if no dates provided
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=1)
        
        with get_db_connection(self.db_path) as conn:
            # Build query with filters
            where_conditions = ["timestamp >= ?", "timestamp <= ?"]
            params = [start_date.isoformat(), end_date.isoformat()]
            
            if user_role:
                where_conditions.append("user_role = ?")
                params.append(user_role.value)
            
            where_clause = " AND ".join(where_conditions)
            
            # Get basic aggregations
            cursor = conn.execute(f"""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(cost_usd) as total_cost,
                    SUM(total_tokens) as total_tokens,
                    AVG(cost_usd) as avg_cost_per_request,
                    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits
                FROM cost_tracking 
                WHERE {where_clause}
            """, params)
            
            basic_stats = cursor.fetchone()
            
            if not basic_stats or basic_stats[0] == 0:
                return self._empty_summary(start_date, end_date)
            
            total_requests = basic_stats[0]
            cache_hit_rate = basic_stats[4] / total_requests if total_requests > 0 else 0.0
            
            # Get cost by model
            cursor = conn.execute(f"""
                SELECT model, SUM(cost_usd) as cost, COUNT(*) as requests
                FROM cost_tracking 
                WHERE {where_clause}
                GROUP BY model
                ORDER BY cost DESC
            """, params)
            
            cost_by_model = {row[0]: {"cost": row[1], "requests": row[2]} 
                           for row in cursor.fetchall()}
            
            # Get cost by role
            cursor = conn.execute(f"""
                SELECT user_role, SUM(cost_usd) as cost, COUNT(*) as requests
                FROM cost_tracking 
                WHERE {where_clause}
                GROUP BY user_role
                ORDER BY cost DESC
            """, params)
            
            cost_by_role = {row[0]: {"cost": row[1], "requests": row[2]} 
                          for row in cursor.fetchall()}
            
            # Get hourly breakdown for trend analysis
            cursor = conn.execute(f"""
                SELECT 
                    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
                    SUM(cost_usd) as cost,
                    COUNT(*) as requests
                FROM cost_tracking 
                WHERE {where_clause}
                GROUP BY hour
                ORDER BY hour
            """, params)
            
            hourly_breakdown = [
                {"hour": row[0], "cost": row[1], "requests": row[2]}
                for row in cursor.fetchall()
            ]
            
            return {
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "summary": {
                    "total_cost_usd": basic_stats[1] or 0.0,
                    "total_requests": total_requests,
                    "total_tokens": basic_stats[2] or 0,
                    "avg_cost_per_request": basic_stats[3] or 0.0,
                    "cache_hit_rate": cache_hit_rate
                },
                "breakdown": {
                    "by_model": cost_by_model,
                    "by_role": cost_by_role,
                    "hourly": hourly_breakdown
                },
                "optimization": self._get_optimization_recommendations(conn, where_clause, params)
            }
    
    def _empty_summary(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Return empty summary structure."""
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_cost_usd": 0.0,
                "total_requests": 0,
                "total_tokens": 0,
                "avg_cost_per_request": 0.0,
                "cache_hit_rate": 0.0
            },
            "breakdown": {
                "by_model": {},
                "by_role": {},
                "hourly": []
            },
            "optimization": {
                "recommendations": [],
                "potential_savings": 0.0
            }
        }
    
    def _get_optimization_recommendations(
        self, 
        conn: sqlite3.Connection, 
        where_clause: str, 
        params: List[Any]
    ) -> Dict[str, Any]:
        """Generate cost optimization recommendations."""
        recommendations = []
        potential_savings = 0.0
        
        # Check for expensive queries that could use cheaper models
        cursor = conn.execute(f"""
            SELECT model, AVG(cost_usd) as avg_cost, COUNT(*) as count
            FROM cost_tracking 
            WHERE {where_clause} AND model = 'gpt-4'
            GROUP BY model
        """, params)
        
        gpt4_stats = cursor.fetchone()
        if gpt4_stats and gpt4_stats[2] > 0:  # Has GPT-4 usage
            # Estimate savings if 50% of GPT-4 queries used GPT-3.5
            gpt4_avg_cost = gpt4_stats[1]
            gpt35_estimated_cost = gpt4_avg_cost * 0.1  # GPT-3.5 is ~10% of GPT-4 cost
            potential_query_savings = (gpt4_avg_cost - gpt35_estimated_cost) * (gpt4_stats[2] * 0.5)
            potential_savings += potential_query_savings
            
            recommendations.append({
                "type": "model_optimization",
                "description": f"Consider using GPT-3.5 for simpler queries. "
                             f"Potential savings: ${potential_query_savings:.2f}",
                "impact": "medium",
                "effort": "low"
            })
        
        # Check cache hit rate
        cursor = conn.execute(f"""
            SELECT 
                SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits,
                COUNT(*) as total_requests,
                AVG(cost_usd) as avg_cost
            FROM cost_tracking 
            WHERE {where_clause}
        """, params)
        
        cache_stats = cursor.fetchone()
        if cache_stats and cache_stats[1] > 0:
            cache_hit_rate = cache_stats[0] / cache_stats[1]
            if cache_hit_rate < 0.2:  # Less than 20% cache hit rate
                avg_cost = cache_stats[2] or 0
                potential_cache_savings = avg_cost * cache_stats[1] * 0.1  # 10% potential savings
                potential_savings += potential_cache_savings
                
                recommendations.append({
                    "type": "caching_optimization",
                    "description": f"Low cache hit rate ({cache_hit_rate:.1%}). "
                                 f"Improve caching strategy. Potential savings: ${potential_cache_savings:.2f}",
                    "impact": "high",
                    "effort": "medium"
                })
        
        # Check for high-cost sessions
        cursor = conn.execute(f"""
            SELECT session_id, SUM(cost_usd) as session_cost, COUNT(*) as requests
            FROM cost_tracking 
            WHERE {where_clause} AND session_id IS NOT NULL
            GROUP BY session_id
            HAVING session_cost > 1.0
            ORDER BY session_cost DESC
            LIMIT 5
        """, params)
        
        expensive_sessions = cursor.fetchall()
        if expensive_sessions:
            total_expensive_cost = sum(row[1] for row in expensive_sessions)
            recommendations.append({
                "type": "session_monitoring",
                "description": f"Monitor high-cost sessions. "
                             f"Top 5 sessions cost ${total_expensive_cost:.2f}",
                "impact": "medium",
                "effort": "low"
            })
        
        return {
            "recommendations": recommendations,
            "potential_savings": potential_savings
        }
    
    def get_expensive_queries(
        self, 
        limit: int = 10,
        min_cost: float = 0.01
    ) -> List[Dict[str, Any]]:
        """
        Get the most expensive queries for optimization analysis.
        
        Args:
            limit: Maximum number of queries to return
            min_cost: Minimum cost threshold
            
        Returns:
            List of expensive queries with details
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    id, timestamp, model, input_tokens, output_tokens, 
                    total_tokens, cost_usd, user_role, session_id, cache_hit
                FROM cost_tracking 
                WHERE cost_usd >= ?
                ORDER BY cost_usd DESC
                LIMIT ?
            """, (min_cost, limit))
            
            expensive_queries = []
            for row in cursor.fetchall():
                expensive_queries.append({
                    "id": row[0],
                    "timestamp": row[1],
                    "model": row[2],
                    "input_tokens": row[3],
                    "output_tokens": row[4],
                    "total_tokens": row[5],
                    "cost_usd": row[6],
                    "user_role": row[7],
                    "session_id": row[8],
                    "cache_hit": bool(row[9]),
                    "cost_per_token": row[6] / row[5] if row[5] > 0 else 0
                })
            
            return expensive_queries
    
    def get_daily_costs(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily cost breakdown for the specified number of days.
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of daily cost summaries
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    SUM(cost_usd) as total_cost,
                    COUNT(*) as total_requests,
                    SUM(total_tokens) as total_tokens,
                    AVG(cost_usd) as avg_cost_per_request,
                    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits
                FROM cost_tracking 
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (start_date.isoformat(), end_date.isoformat()))
            
            daily_costs = []
            for row in cursor.fetchall():
                total_requests = row[2]
                cache_hit_rate = row[5] / total_requests if total_requests > 0 else 0.0
                
                daily_costs.append({
                    "date": row[0],
                    "total_cost": row[1] or 0.0,
                    "total_requests": total_requests,
                    "total_tokens": row[3] or 0,
                    "avg_cost_per_request": row[4] or 0.0,
                    "cache_hit_rate": cache_hit_rate
                })
            
            return daily_costs
    
    def get_role_analytics(self) -> Dict[str, Any]:
        """
        Get detailed analytics by user role.
        
        Returns:
            Dict with role-based analytics
        """
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    user_role,
                    COUNT(*) as total_requests,
                    SUM(cost_usd) as total_cost,
                    AVG(cost_usd) as avg_cost_per_request,
                    SUM(total_tokens) as total_tokens,
                    AVG(total_tokens) as avg_tokens_per_request,
                    SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits
                FROM cost_tracking 
                GROUP BY user_role
                ORDER BY total_cost DESC
            """)
            
            role_analytics = {}
            for row in cursor.fetchall():
                role = row[0]
                total_requests = row[1]
                cache_hit_rate = row[6] / total_requests if total_requests > 0 else 0.0
                
                role_analytics[role] = {
                    "total_requests": total_requests,
                    "total_cost": row[2] or 0.0,
                    "avg_cost_per_request": row[3] or 0.0,
                    "total_tokens": row[4] or 0,
                    "avg_tokens_per_request": row[5] or 0.0,
                    "cache_hit_rate": cache_hit_rate
                }
            
            return role_analytics
    
    def set_budget_alert(
        self, 
        budget_limit: float, 
        period_hours: int = 24,
        user_role: Optional[UserRole] = None
    ) -> bool:
        """
        Check if current spending exceeds budget limit.
        
        Args:
            budget_limit: Budget limit in USD
            period_hours: Time period for budget check
            user_role: Optional role filter
            
        Returns:
            True if budget is exceeded
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=period_hours)
        
        summary = self.get_cost_summary(start_date, end_date, user_role)
        current_cost = summary["summary"]["total_cost_usd"]
        
        if current_cost >= budget_limit:
            logger.warning(
                f"Budget alert: Current cost ${current_cost:.2f} "
                f"exceeds limit ${budget_limit:.2f} for {period_hours}h period"
            )
            return True
        
        return False
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """
        Clean up old cost tracking data.
        
        Args:
            days_to_keep: Number of days of data to retain
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        with get_db_connection(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM cost_tracking 
                WHERE timestamp < ?
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            logger.info(f"Cleaned up {deleted_count} old cost tracking records")
            return deleted_count