"""
Role-Based Access Control (RBAC) implementation.
Defines roles, permissions, and access control logic.
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from ..models import UserRole


@dataclass
class RoleConfig:
    """Configuration for a user role."""
    role: UserRole
    max_queries_per_hour: int
    allowed_models: List[str]
    features: List[str]
    max_tokens_per_query: int
    cost_limit_per_hour: float
    description: str


class RBACService:
    """Role-Based Access Control service."""
    
    # Role configurations
    ROLE_CONFIGS = {
        UserRole.PATIENT: RoleConfig(
            role=UserRole.PATIENT,
            max_queries_per_hour=10,
            allowed_models=["gpt-3.5-turbo"],
            features=[
                "basic_chat",
                "symptom_checker", 
                "health_information",
                "appointment_scheduling"
            ],
            max_tokens_per_query=500,
            cost_limit_per_hour=1.00,
            description="Basic user with limited access to health information"
        ),
        UserRole.PHYSICIAN: RoleConfig(
            role=UserRole.PHYSICIAN,
            max_queries_per_hour=100,
            allowed_models=["gpt-3.5-turbo", "gpt-4"],
            features=[
                "basic_chat",
                "advanced_chat",
                "diagnosis_support",
                "research_access",
                "clinical_guidelines",
                "drug_interactions",
                "medical_calculations"
            ],
            max_tokens_per_query=1000,
            cost_limit_per_hour=10.00,
            description="Medical professional with advanced AI capabilities"
        ),
        UserRole.ADMIN: RoleConfig(
            role=UserRole.ADMIN,
            max_queries_per_hour=1000,
            allowed_models=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
            features=[
                "all",  # Special marker for all features
                "metrics_access",
                "audit_logs",
                "user_management",
                "system_configuration",
                "security_monitoring"
            ],
            max_tokens_per_query=2000,
            cost_limit_per_hour=50.00,
            description="System administrator with full access"
        )
    }
    
    def __init__(self):
        self.role_configs = self.ROLE_CONFIGS.copy()
    
    def get_role_config(self, user_role: UserRole) -> Optional[RoleConfig]:
        """Get configuration for a specific role."""
        return self.role_configs.get(user_role)
    
    def authorize_feature(self, user_role: UserRole, feature: str) -> bool:
        """
        Check if a user role is authorized to access a specific feature.
        
        Args:
            user_role: User's role
            feature: Feature name to check access for
            
        Returns:
            True if authorized, False otherwise
        """
        role_config = self.get_role_config(user_role)
        if not role_config:
            return False
        
        # Admin has access to all features
        if "all" in role_config.features:
            return True
            
        return feature in role_config.features
    
    def authorize_model(self, user_role: UserRole, model: str) -> bool:
        """
        Check if a user role is authorized to use a specific model.
        
        Args:
            user_role: User's role
            model: Model name to check access for
            
        Returns:
            True if authorized, False otherwise
        """
        role_config = self.get_role_config(user_role)
        if not role_config:
            return False
            
        return model in role_config.allowed_models
    
    def get_max_queries_per_hour(self, user_role: UserRole) -> int:
        """Get maximum queries per hour for a role."""
        role_config = self.get_role_config(user_role)
        return role_config.max_queries_per_hour if role_config else 0
    
    def get_max_tokens_per_query(self, user_role: UserRole) -> int:
        """Get maximum tokens per query for a role."""
        role_config = self.get_role_config(user_role)
        return role_config.max_tokens_per_query if role_config else 0
    
    def get_cost_limit_per_hour(self, user_role: UserRole) -> float:
        """Get cost limit per hour for a role."""
        role_config = self.get_role_config(user_role)
        return role_config.cost_limit_per_hour if role_config else 0.0
    
    def get_allowed_features(self, user_role: UserRole) -> List[str]:
        """Get list of features allowed for a role."""
        role_config = self.get_role_config(user_role)
        return role_config.features.copy() if role_config else []
    
    def get_allowed_models(self, user_role: UserRole) -> List[str]:
        """Get list of models allowed for a role."""
        role_config = self.get_role_config(user_role)
        return role_config.allowed_models.copy() if role_config else []
    
    def validate_request_limits(
        self, 
        user_role: UserRole, 
        token_count: int, 
        estimated_cost: float
    ) -> Dict[str, bool]:
        """
        Validate if a request is within role limits.
        
        Args:
            user_role: User's role
            token_count: Number of tokens in the request
            estimated_cost: Estimated cost of the request
            
        Returns:
            Dictionary with validation results
        """
        role_config = self.get_role_config(user_role)
        if not role_config:
            return {
                "valid": False,
                "token_limit_ok": False,
                "cost_limit_ok": False,
                "reason": "Invalid role"
            }
        
        token_limit_ok = token_count <= role_config.max_tokens_per_query
        cost_limit_ok = estimated_cost <= role_config.cost_limit_per_hour
        
        return {
            "valid": token_limit_ok and cost_limit_ok,
            "token_limit_ok": token_limit_ok,
            "cost_limit_ok": cost_limit_ok,
            "max_tokens": role_config.max_tokens_per_query,
            "cost_limit": role_config.cost_limit_per_hour,
            "reason": None if (token_limit_ok and cost_limit_ok) else "Limits exceeded"
        }
    
    def get_role_summary(self, user_role: UserRole) -> Dict[str, any]:
        """Get a summary of role capabilities."""
        role_config = self.get_role_config(user_role)
        if not role_config:
            return {"error": "Invalid role"}
        
        return {
            "role": role_config.role.value,
            "description": role_config.description,
            "max_queries_per_hour": role_config.max_queries_per_hour,
            "allowed_models": role_config.allowed_models,
            "features": role_config.features,
            "max_tokens_per_query": role_config.max_tokens_per_query,
            "cost_limit_per_hour": role_config.cost_limit_per_hour
        }
    
    def compare_roles(self) -> Dict[str, Dict[str, any]]:
        """Get a comparison of all roles and their capabilities."""
        return {
            role.value: self.get_role_summary(role) 
            for role in UserRole
        }