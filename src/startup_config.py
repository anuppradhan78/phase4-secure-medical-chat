"""
Startup Configuration Checker

This module provides configuration validation and initialization
that should be run when the application starts up.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from .config import ConfigManager, ConfigurationError, AppConfig


class StartupConfigChecker:
    """Validates configuration and environment on application startup."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def validate_startup_config(self) -> Tuple[bool, AppConfig, List[str], List[str]]:
        """
        Validate configuration on startup.
        
        Returns:
            Tuple of (success, config, warnings, errors)
        """
        print("🚀 Starting Secure Medical Chat Configuration Validation...")
        print("=" * 60)
        
        try:
            # Load configuration
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            # Run validation checks
            self._check_required_files(config)
            self._check_api_keys(config)
            self._check_security_settings(config)
            self._check_cost_settings(config)
            self._check_database_settings(config)
            self._check_environment_specific(config)
            
            # Display results
            self._display_validation_results(config)
            
            success = len(self.errors) == 0
            return success, config, self.warnings, self.errors
            
        except ConfigurationError as e:
            self.errors.append(f"Configuration error: {str(e)}")
            print(f"❌ Configuration Error: {str(e)}")
            return False, None, self.warnings, self.errors
        
        except Exception as e:
            self.errors.append(f"Unexpected error during configuration validation: {str(e)}")
            print(f"❌ Unexpected Error: {str(e)}")
            return False, None, self.warnings, self.errors
    
    def _check_required_files(self, config: AppConfig):
        """Check that required files and directories exist."""
        print("\n📁 Checking Required Files and Directories...")
        
        # Check guardrails config if enabled
        if config.security.enable_guardrails:
            guardrails_path = Path(config.security.guardrails_config_path)
            if not guardrails_path.exists():
                self.warnings.append(
                    f"Guardrails config directory not found: {guardrails_path}. "
                    "Guardrails may not work properly."
                )
                print(f"⚠️  Guardrails config directory not found: {guardrails_path}")
            else:
                print(f"✅ Guardrails config directory found: {guardrails_path}")
        
        # Check database directory
        db_url = config.database.url
        if db_url.startswith("sqlite:///"):
            db_path = Path(db_url.replace("sqlite:///", ""))
            db_dir = db_path.parent
            if not db_dir.exists():
                try:
                    db_dir.mkdir(parents=True, exist_ok=True)
                    print(f"✅ Created database directory: {db_dir}")
                except Exception as e:
                    self.errors.append(f"Cannot create database directory {db_dir}: {str(e)}")
                    print(f"❌ Cannot create database directory {db_dir}: {str(e)}")
            else:
                print(f"✅ Database directory exists: {db_dir}")
    
    def _check_api_keys(self, config: AppConfig):
        """Check API key configuration."""
        print("\n🔑 Checking API Key Configuration...")
        
        # Check OpenAI API key
        if not config.llm.api_key or config.llm.api_key.startswith("sk-your-"):
            self.errors.append("OPENAI_API_KEY is not properly configured")
            print("❌ OPENAI_API_KEY is not properly configured")
        elif config.llm.api_key.startswith("sk-"):
            print("✅ OPENAI_API_KEY appears to be properly formatted")
        else:
            self.warnings.append("OPENAI_API_KEY format may be incorrect (should start with 'sk-')")
            print("⚠️  OPENAI_API_KEY format may be incorrect")
        
        # Check Helicone API key if cost tracking is enabled
        if config.cost.enable_cost_tracking:
            if not config.cost.helicone_api_key:
                self.warnings.append(
                    "Cost tracking is enabled but HELICONE_API_KEY is not set. "
                    "Cost tracking features may not work."
                )
                print("⚠️  HELICONE_API_KEY not set (cost tracking may not work)")
            elif config.cost.helicone_api_key.startswith("sk-helicone-"):
                print("✅ HELICONE_API_KEY appears to be properly formatted")
            else:
                self.warnings.append("HELICONE_API_KEY format may be incorrect")
                print("⚠️  HELICONE_API_KEY format may be incorrect")
    
    def _check_security_settings(self, config: AppConfig):
        """Check security configuration."""
        print("\n🔒 Checking Security Configuration...")
        
        # Check JWT secret
        if config.auth.jwt_secret_key == "your-super-secret-jwt-key-change-this-in-production":
            if config.environment.value == "production":
                self.errors.append("JWT_SECRET_KEY must be changed from default in production")
                print("❌ JWT_SECRET_KEY must be changed from default in production")
            else:
                self.warnings.append("JWT_SECRET_KEY is using default value")
                print("⚠️  JWT_SECRET_KEY is using default value")
        elif len(config.auth.jwt_secret_key) < 32:
            self.warnings.append("JWT_SECRET_KEY should be at least 32 characters long")
            print("⚠️  JWT_SECRET_KEY should be longer for better security")
        else:
            print("✅ JWT_SECRET_KEY appears to be properly configured")
        
        # Check PII entities
        if not config.security.presidio_entities:
            self.errors.append("PRESIDIO_ENTITIES cannot be empty")
            print("❌ PRESIDIO_ENTITIES cannot be empty")
        elif len(config.security.presidio_entities) < 3:
            self.warnings.append("Consider adding more PII entity types for better protection")
            print("⚠️  Consider adding more PII entity types")
        else:
            print(f"✅ PII detection configured for {len(config.security.presidio_entities)} entity types")
        
        # Check security features
        security_features = [
            ("PII Redaction", config.security.enable_pii_redaction),
            ("Guardrails", config.security.enable_guardrails),
            ("Medical Disclaimers", config.security.enable_medical_disclaimers)
        ]
        
        enabled_features = [name for name, enabled in security_features if enabled]
        if len(enabled_features) < 2:
            self.warnings.append("Consider enabling more security features for better protection")
            print("⚠️  Consider enabling more security features")
        
        print(f"✅ Security features enabled: {', '.join(enabled_features)}")
    
    def _check_cost_settings(self, config: AppConfig):
        """Check cost and optimization settings."""
        print("\n💰 Checking Cost Configuration...")
        
        # Check daily cost limit
        if config.cost.daily_limit <= 0:
            self.errors.append("COST_LIMIT_DAILY must be greater than 0")
            print("❌ COST_LIMIT_DAILY must be greater than 0")
        elif config.cost.daily_limit < 10:
            self.warnings.append("Daily cost limit is very low, may limit functionality")
            print("⚠️  Daily cost limit is very low")
        else:
            print(f"✅ Daily cost limit set to ${config.cost.daily_limit}")
        
        # Check cost alert threshold
        if config.cost.cost_alert_threshold >= 100:
            self.warnings.append("Cost alert threshold should be less than 100%")
            print("⚠️  Cost alert threshold should be less than 100%")
        else:
            alert_amount = config.cost.daily_limit * (config.cost.cost_alert_threshold / 100)
            print(f"✅ Cost alerts will trigger at ${alert_amount:.2f} ({config.cost.cost_alert_threshold}%)")
        
        # Check caching settings
        if config.cost.enable_response_cache:
            print(f"✅ Response caching enabled (TTL: {config.cost.cache_ttl_hours} hours)")
        else:
            self.warnings.append("Response caching is disabled, may increase costs")
            print("⚠️  Response caching is disabled")
    
    def _check_database_settings(self, config: AppConfig):
        """Check database configuration."""
        print("\n🗄️  Checking Database Configuration...")
        
        db_url = config.database.url
        if db_url.startswith("sqlite:///"):
            db_path = Path(db_url.replace("sqlite:///", ""))
            if db_path.exists():
                print(f"✅ SQLite database file exists: {db_path}")
            else:
                print(f"ℹ️  SQLite database will be created: {db_path}")
        elif db_url.startswith("postgresql://"):
            print("ℹ️  PostgreSQL database configured")
            # Could add connection test here
        else:
            self.warnings.append(f"Unknown database URL format: {db_url}")
            print(f"⚠️  Unknown database URL format: {db_url}")
    
    def _check_environment_specific(self, config: AppConfig):
        """Check environment-specific settings."""
        print(f"\n🌍 Checking {config.environment.value.title()} Environment Settings...")
        
        if config.environment.value == "production":
            # Production-specific checks
            if config.debug:
                self.warnings.append("DEBUG is enabled in production")
                print("⚠️  DEBUG is enabled in production")
            
            if config.log_level.value == "DEBUG":
                self.warnings.append("DEBUG logging enabled in production")
                print("⚠️  DEBUG logging enabled in production")
            
            if not config.security.enable_pii_redaction:
                self.errors.append("PII redaction must be enabled in production")
                print("❌ PII redaction must be enabled in production")
            
            if not config.security.enable_guardrails:
                self.warnings.append("Consider enabling guardrails in production")
                print("⚠️  Consider enabling guardrails in production")
            
            print("✅ Production environment checks completed")
        
        elif config.environment.value == "development":
            # Development-specific checks
            if not config.debug:
                self.warnings.append("Consider enabling DEBUG in development")
                print("⚠️  Consider enabling DEBUG in development")
            
            print("✅ Development environment checks completed")
    
    def _display_validation_results(self, config: AppConfig):
        """Display validation results summary."""
        print("\n" + "=" * 60)
        print("📊 CONFIGURATION VALIDATION SUMMARY")
        print("=" * 60)
        
        # Configuration overview
        print(f"Environment: {config.environment.value}")
        print(f"LLM Provider: {config.llm.provider.value}")
        print(f"Default Model: {config.llm.default_model}")
        print(f"Daily Cost Limit: ${config.cost.daily_limit}")
        
        # Security summary
        security_score = sum([
            config.security.enable_pii_redaction,
            config.security.enable_guardrails,
            config.security.enable_medical_disclaimers
        ])
        print(f"Security Features: {security_score}/3 enabled")
        
        # Results summary
        print(f"\nValidation Results:")
        print(f"  ✅ Errors: {len(self.errors)}")
        print(f"  ⚠️  Warnings: {len(self.warnings)}")
        
        # Display errors
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        # Display warnings
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        # Final status
        if self.errors:
            print(f"\n❌ Configuration validation FAILED. Please fix the errors above.")
        elif self.warnings:
            print(f"\n⚠️  Configuration validation PASSED with warnings.")
        else:
            print(f"\n🎉 Configuration validation PASSED successfully!")


def validate_startup_configuration() -> Tuple[bool, Optional[AppConfig]]:
    """
    Validate configuration on application startup.
    
    Returns:
        Tuple of (success, config or None)
    """
    checker = StartupConfigChecker()
    success, config, warnings, errors = checker.validate_startup_config()
    
    if not success:
        print("\n💡 Configuration Help:")
        print("  1. Check your .env file exists and has required variables")
        print("  2. Copy from .env.example if needed")
        print("  3. Set proper API keys (OPENAI_API_KEY, HELICONE_API_KEY)")
        print("  4. Run 'python src/config_validator.py' for detailed testing")
        print("  5. See 'examples/config_examples.py' for configuration examples")
        
        return False, None
    
    return True, config


def main():
    """Run startup configuration validation."""
    success, config = validate_startup_configuration()
    
    if success:
        print(f"\n🚀 Ready to start Secure Medical Chat!")
        return 0
    else:
        print(f"\n🛑 Cannot start application due to configuration errors.")
        return 1


if __name__ == "__main__":
    sys.exit(main())