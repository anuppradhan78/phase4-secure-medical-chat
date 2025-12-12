"""
JWT token generation and validation for authentication.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..models import UserRole


class JWTHandler:
    """Handles JWT token generation and validation."""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def create_access_token(
        self, 
        user_id: str, 
        user_role: UserRole, 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token for a user.
        
        Args:
            user_id: Unique user identifier
            user_role: User's role (patient, physician, admin)
            expires_delta: Optional custom expiration time
            
        Returns:
            JWT token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode = {
            "sub": user_id,
            "role": user_role.value,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token has expired
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return None
            
            # Validate required fields
            if not payload.get("sub") or not payload.get("role"):
                return None
                
            return payload
            
        except JWTError:
            return None
    
    def get_user_from_token(self, token: str) -> Optional[Dict[str, str]]:
        """
        Extract user information from a valid JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Dictionary with user_id and user_role or None if invalid
        """
        payload = self.verify_token(token)
        if not payload:
            return None
            
        try:
            user_role = UserRole(payload["role"])
            return {
                "user_id": payload["sub"],
                "user_role": user_role.value
            }
        except (KeyError, ValueError):
            return None
    
    def create_demo_token(self, user_role: UserRole, user_id: Optional[str] = None) -> str:
        """
        Create a demo token for testing purposes.
        
        Args:
            user_role: Role for the demo user
            user_id: Optional user ID (defaults to role-based ID)
            
        Returns:
            JWT token string
        """
        if not user_id:
            user_id = f"demo_{user_role.value}_user"
            
        return self.create_access_token(user_id, user_role)
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)