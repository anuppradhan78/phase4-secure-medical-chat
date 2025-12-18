"""
Configuration management for Secure Medical Chat system.

This module handles environment-based configuration with validation,
type conversion, and clear error messages for missing required settings.
"""

import os
import logging
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"


class Environment(str, Enum):
    """Application environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: LLMProvider
    api_key: str
    default_model: str = "gpt-3.5-turbo"
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 30


@dataclass
class CostConfig:
    """Cost tracking and optimization configuration."""
    helicone_api_key: Optional[str] = None
    daily_limit: float = 100.0
    enable_cost_tracking: bool = True
    enable_response_cache: bool = True
    cache_ttl_hours: int = 24
    cost_alert_threshold: float = 80.0  # Percentage of daily limit


@dataclass
class SecurityConfig:
    """Security and privacy configuration."""
    presidio_entities: List[str] = field(default_factory=lambda: [
        "PERSON", "DATE_TIME", "PHONE_NUMBER", "EMAIL_ADDRESS", 
        "MEDICAL_LICENSE", "US_SSN", "LOCATION"
    ])
    enable_pii_redaction: bool = True
    enable_guardrails: bool = True
    enable_llama_guard: bool = True
    enable_nemo_guardrails: bool = True
    enable_medical_disclaimers: bool = True
    guardrails_config_path: str = "config/guardrails"
    presidio_log_level: LogLevel = LogLevel.INFO


@dataclass
class AuthConfig:
    """Authentication and authorization configuration."""
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    enable_rbac: bool = True


@dataclass
class RateLimitConfig:
    """Rate limiting configuration per user role."""
    patient_max_queries_per_hour: int = 10
    physician_max_queries_per_hour: int = 100
    admin_max_queries_per_hour: int = 1000
    enable_rate_limiting: bool = True


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///./secure_medical_chat.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class AppConfig:
    """Main application configuration."""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    log_level: LogLevel = LogLevel.INFO
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Component configurations
    llm: LLMConfig = None
    cost: CostConfig = field(default_factory=CostConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    auth: AuthConfig = None
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required values."""
    pass


class ConfigManager:
    """Manages application configuration from environment variables."""
    
    def __init__(self):
        self.config: Optional[AppConfig] = None
        self._logger = logging.getLogger(__name__)
    
    def load_config(self) -> AppConfig:
        """Load configuration from environment variables with validation."""
        try:
            # Load main app config
            environment = Environment(os.getenv("ENVIRONMENT", "development"))
            debug = self._get_bool("DEBUG", False)
            log_level = LogLevel(os.getenv("LOG_LEVEL", "INFO"))
            
            # Load LLM config
            llm_config = self._load_llm_config()
            
            # Load cost config
            cost_config = self._load_cost_config()
            
            # Load security config
            security_config = self._load_security_config()
            
            # Load auth config
            auth_config = self._load_auth_config()
            
            # Load rate limit config
            rate_limit_config = self._load_rate_limit_config()
            
            # Load database config
            database_config = self._load_database_config()
            
            self.config = AppConfig(
                environment=environment,
                debug=debug,
                log_level=log_level,
                host=os.getenv("HOST", "0.0.0.0"),
                port=int(os.getenv("PORT", "8000")),
                llm=llm_config,
                cost=cost_config,
                security=security_config,
                auth=auth_config,
                rate_limit=rate_limit_config,
                database=database_config
            )
            
            # Validate configuration
            self._validate_config()
            
            self._logger.info(f"Configuration loaded successfully for {environment} environment")
            return self.config
            
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            self._logger.error(error_msg)
            raise ConfigurationError(error_msg) from e
    
    def _load_llm_config(self) -> LLMConfig:
        """Load LLM configuration."""
        provider_str = self._get_required("LLM_PROVIDER")
        try:
            provider = LLMProvider(provider_str.lower())
        except ValueError:
            raise ConfigurationError(
                f"Invalid LLM_PROVIDER '{provider_str}'. "
                f"Must be one of: {', '.join([p.value for p in LLMProvider])}"
            )
        
        api_key = self._get_required("OPENAI_API_KEY")  # For now, only OpenAI
        
        return LLMConfig(
            provider=provider,
            api_key=api_key,
            default_model=os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo"),
            max_tokens=int(os.getenv("MAX_TOKENS", "1000")),
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            timeout=int(os.getenv("LLM_TIMEOUT", "30"))
        )
    
    def _load_cost_config(self) -> CostConfig:
        """Load cost tracking configuration."""
        return CostConfig(
            helicone_api_key=os.getenv("HELICONE_API_KEY"),
            daily_limit=float(os.getenv("COST_LIMIT_DAILY", "100.0")),
            enable_cost_tracking=self._get_bool("ENABLE_COST_TRACKING", True),
            enable_response_cache=self._get_bool("ENABLE_RESPONSE_CACHE", True),
            cache_ttl_hours=int(os.getenv("CACHE_TTL_HOURS", "24")),
            cost_alert_threshold=float(os.getenv("COST_ALERT_THRESHOLD", "80.0"))
        )
    
    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration."""
        entities_str = os.getenv("PRESIDIO_ENTITIES", 
                                "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION")
        entities = [e.strip() for e in entities_str.split(",") if e.strip()]
        
        return SecurityConfig(
            presidio_entities=entities,
            enable_pii_redaction=self._get_bool("ENABLE_PII_REDACTION", True),
            enable_guardrails=self._get_bool("ENABLE_GUARDRAILS", True),
            enable_llama_guard=self._get_bool("ENABLE_LLAMA_GUARD", True),
            enable_nemo_guardrails=self._get_bool("ENABLE_NEMO_GUARDRAILS", True),
            enable_medical_disclaimers=self._get_bool("ENABLE_MEDICAL_DISCLAIMERS", True),
            guardrails_config_path=os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails"),
            presidio_log_level=LogLevel(os.getenv("PRESIDIO_LOG_LEVEL", "INFO"))
        )
    
    def _load_auth_config(self) -> AuthConfig:
        """Load authentication configuration."""
        jwt_secret = self._get_required("JWT_SECRET_KEY")
        
        return AuthConfig(
            jwt_secret_key=jwt_secret,
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "1440")),
            enable_rbac=self._get_bool("ENABLE_RBAC", True)
        )
    
    def _load_rate_limit_config(self) -> RateLimitConfig:
        """Load rate limiting configuration."""
        return RateLimitConfig(
            patient_max_queries_per_hour=int(os.getenv("PATIENT_MAX_QUERIES_PER_HOUR", "10")),
            physician_max_queries_per_hour=int(os.getenv("PHYSICIAN_MAX_QUERIES_PER_HOUR", "100")),
            admin_max_queries_per_hour=int(os.getenv("ADMIN_MAX_QUERIES_PER_HOUR", "1000")),
            enable_rate_limiting=self._get_bool("ENABLE_RATE_LIMITING", True)
        )
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration."""
        return DatabaseConfig(
            url=os.getenv("DATABASE_URL", "sqlite:///./secure_medical_chat.db"),
            echo=self._get_bool("DATABASE_ECHO", False),
            pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
        )
    
    def _validate_config(self):
        """Validate the loaded configuration."""
        if not self.config:
            raise ConfigurationError("Configuration not loaded")
        
        # Validate LLM configuration
        if not self.config.llm.api_key:
            raise ConfigurationError("OPENAI_API_KEY is required")
        
        # Validate JWT secret in production
        if (self.config.environment == Environment.PRODUCTION and 
            self.config.auth.jwt_secret_key == "your-super-secret-jwt-key-change-this-in-production"):
            raise ConfigurationError(
                "JWT_SECRET_KEY must be changed from default value in production"
            )
        
        # Validate cost limits
        if self.config.cost.daily_limit <= 0:
            raise ConfigurationError("COST_LIMIT_DAILY must be greater than 0")
        
        # Validate rate limits
        if (self.config.rate_limit.patient_max_queries_per_hour <= 0 or
            self.config.rate_limit.physician_max_queries_per_hour <= 0 or
            self.config.rate_limit.admin_max_queries_per_hour <= 0):
            raise ConfigurationError("All rate limits must be greater than 0")
        
        # Validate Presidio entities
        if not self.config.security.presidio_entities:
            raise ConfigurationError("PRESIDIO_ENTITIES cannot be empty")
        
        # Validate guardrails config path exists if guardrails are enabled
        if (self.config.security.enable_guardrails and 
            not os.path.exists(self.config.security.guardrails_config_path)):
            self._logger.warning(
                f"Guardrails config path does not exist: {self.config.security.guardrails_config_path}"
            )
    
    def _get_required(self, key: str) -> str:
        """Get a required environment variable."""
        value = os.getenv(key)
        if not value:
            raise ConfigurationError(f"Required environment variable {key} is not set")
        return value
    
    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")
    
    def get_config(self) -> AppConfig:
        """Get the current configuration."""
        if not self.config:
            raise ConfigurationError("Configuration not loaded. Call load_config() first.")
        return self.config
    
    def reload_config(self) -> AppConfig:
        """Reload configuration from environment variables."""
        return self.load_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration (excluding sensitive data)."""
        if not self.config:
            return {"error": "Configuration not loaded"}
        
        return {
            "environment": self.config.environment.value,
            "debug": self.config.debug,
            "log_level": self.config.log_level.value,
            "llm": {
                "provider": self.config.llm.provider.value,
                "default_model": self.config.llm.default_model,
                "max_tokens": self.config.llm.max_tokens,
                "temperature": self.config.llm.temperature,
                "api_key_configured": bool(self.config.llm.api_key)
            },
            "cost": {
                "daily_limit": self.config.cost.daily_limit,
                "enable_cost_tracking": self.config.cost.enable_cost_tracking,
                "enable_response_cache": self.config.cost.enable_response_cache,
                "cache_ttl_hours": self.config.cost.cache_ttl_hours,
                "helicone_configured": bool(self.config.cost.helicone_api_key)
            },
            "security": {
                "presidio_entities": self.config.security.presidio_entities,
                "enable_pii_redaction": self.config.security.enable_pii_redaction,
                "enable_guardrails": self.config.security.enable_guardrails,
                "enable_llama_guard": self.config.security.enable_llama_guard,
                "enable_nemo_guardrails": self.config.security.enable_nemo_guardrails,
                "enable_medical_disclaimers": self.config.security.enable_medical_disclaimers
            },
            "rate_limits": {
                "patient": self.config.rate_limit.patient_max_queries_per_hour,
                "physician": self.config.rate_limit.physician_max_queries_per_hour,
                "admin": self.config.rate_limit.admin_max_queries_per_hour,
                "enabled": self.config.rate_limit.enable_rate_limiting
            },
            "database": {
                "url": self.config.database.url.replace(os.path.expanduser("~"), "~"),  # Hide full path
                "echo": self.config.database.echo
            }
        }


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> AppConfig:
    """Get the current application configuration."""
    return config_manager.get_config()


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    return config_manager.load_config()


def reload_config() -> AppConfig:
    """Reload configuration from environment variables."""
    return config_manager.reload_config()