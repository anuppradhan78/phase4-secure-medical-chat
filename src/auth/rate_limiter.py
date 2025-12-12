"""
Rate limiting implementation for different user roles.
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from ..models import UserRole


class RateLimiter:
    """Rate limiter with role-based limits."""
    
    def __init__(self):
        # Store request timestamps for each user
        self.user_requests: Dict[str, deque] = defaultdict(deque)
        # Store cost tracking for each user
        self.user_costs: Dict[str, deque] = defaultdict(deque)
        # Role-based limits (requests per hour)
        self.role_limits = {
            UserRole.PATIENT: 10,
            UserRole.PHYSICIAN: 100,
            UserRole.ADMIN: 1000
        }
        # Cost limits per hour (USD)
        self.cost_limits = {
            UserRole.PATIENT: 1.00,
            UserRole.PHYSICIAN: 10.00,
            UserRole.ADMIN: 50.00
        }
    
    def _cleanup_old_requests(self, user_id: str, window_hours: int = 1):
        """Remove requests older than the specified window."""
        cutoff_time = time.time() - (window_hours * 3600)
        
        # Clean up request timestamps
        while self.user_requests[user_id] and self.user_requests[user_id][0] < cutoff_time:
            self.user_requests[user_id].popleft()
        
        # Clean up cost records
        while self.user_costs[user_id] and self.user_costs[user_id][0][0] < cutoff_time:
            self.user_costs[user_id].popleft()
    
    def check_rate_limit(self, user_id: str, user_role: UserRole) -> Tuple[bool, Dict[str, any]]:
        """
        Check if user is within rate limits.
        
        Args:
            user_id: User identifier
            user_role: User's role
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        self._cleanup_old_requests(user_id)
        
        current_requests = len(self.user_requests[user_id])
        limit = self.role_limits.get(user_role, 0)
        
        allowed = current_requests < limit
        
        info = {
            "allowed": allowed,
            "current_requests": current_requests,
            "limit": limit,
            "remaining": max(0, limit - current_requests),
            "reset_time": datetime.now(timezone.utc) + timedelta(hours=1),
            "window_hours": 1
        }
        
        return allowed, info
    
    def check_cost_limit(self, user_id: str, user_role: UserRole, additional_cost: float = 0.0) -> Tuple[bool, Dict[str, any]]:
        """
        Check if user is within cost limits.
        
        Args:
            user_id: User identifier
            user_role: User's role
            additional_cost: Additional cost to check against limit
            
        Returns:
            Tuple of (allowed, info_dict)
        """
        self._cleanup_old_requests(user_id)
        
        # Calculate current cost in the last hour
        current_cost = sum(cost for _, cost in self.user_costs[user_id])
        total_cost = current_cost + additional_cost
        
        limit = self.cost_limits.get(user_role, 0.0)
        allowed = total_cost <= limit
        
        info = {
            "allowed": allowed,
            "current_cost": current_cost,
            "additional_cost": additional_cost,
            "total_cost": total_cost,
            "limit": limit,
            "remaining": max(0.0, limit - total_cost),
            "reset_time": datetime.now(timezone.utc) + timedelta(hours=1),
            "window_hours": 1
        }
        
        return allowed, info
    
    def record_request(self, user_id: str, cost: float = 0.0):
        """
        Record a request for rate limiting.
        
        Args:
            user_id: User identifier
            cost: Cost of the request in USD
        """
        current_time = time.time()
        
        # Record request timestamp
        self.user_requests[user_id].append(current_time)
        
        # Record cost if provided
        if cost > 0:
            self.user_costs[user_id].append((current_time, cost))
        
        # Keep only recent requests to prevent memory bloat
        self._cleanup_old_requests(user_id)
    
    def get_user_stats(self, user_id: str, user_role: UserRole) -> Dict[str, any]:
        """
        Get current statistics for a user.
        
        Args:
            user_id: User identifier
            user_role: User's role
            
        Returns:
            Dictionary with user statistics
        """
        self._cleanup_old_requests(user_id)
        
        current_requests = len(self.user_requests[user_id])
        current_cost = sum(cost for _, cost in self.user_costs[user_id])
        
        request_limit = self.role_limits.get(user_role, 0)
        cost_limit = self.cost_limits.get(user_role, 0.0)
        
        return {
            "user_id": user_id,
            "user_role": user_role.value,
            "requests": {
                "current": current_requests,
                "limit": request_limit,
                "remaining": max(0, request_limit - current_requests),
                "percentage_used": (current_requests / request_limit * 100) if request_limit > 0 else 0
            },
            "cost": {
                "current": round(current_cost, 4),
                "limit": cost_limit,
                "remaining": round(max(0.0, cost_limit - current_cost), 4),
                "percentage_used": (current_cost / cost_limit * 100) if cost_limit > 0 else 0
            },
            "reset_time": datetime.now(timezone.utc) + timedelta(hours=1)
        }
    
    def get_all_limits(self) -> Dict[str, Dict[str, any]]:
        """Get rate limits for all roles."""
        return {
            role.value: {
                "requests_per_hour": self.role_limits[role],
                "cost_limit_per_hour": self.cost_limits[role]
            }
            for role in UserRole
        }
    
    def reset_user_limits(self, user_id: str):
        """Reset rate limits for a specific user (admin function)."""
        if user_id in self.user_requests:
            self.user_requests[user_id].clear()
        if user_id in self.user_costs:
            self.user_costs[user_id].clear()
    
    def is_approaching_limit(self, user_id: str, user_role: UserRole, threshold: float = 0.8) -> Dict[str, bool]:
        """
        Check if user is approaching their limits.
        
        Args:
            user_id: User identifier
            user_role: User's role
            threshold: Threshold percentage (0.0 to 1.0)
            
        Returns:
            Dictionary indicating which limits are being approached
        """
        stats = self.get_user_stats(user_id, user_role)
        
        return {
            "requests": stats["requests"]["percentage_used"] >= (threshold * 100),
            "cost": stats["cost"]["percentage_used"] >= (threshold * 100)
        }