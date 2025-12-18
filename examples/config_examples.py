"""
Configuration Examples for Secure Medical Chat

This script demonstrates various configuration scenarios and how to use
the configuration system in different environments and use cases.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import ConfigManager, get_config, load_config


class ConfigExamples:
    """Demonstrates different configuration scenarios."""
    
    def __init__(self):
        self.examples = []
    
    def run_all_examples(self):
        """Run all configuration examples."""
        print("🔧 Configuration Examples for Secure Medical Chat")
        print("=" * 60)
        
        examples = [
            ("Development Environment", self.development_config_example),
            ("Production Environment", self.production_config_example),
            ("High-Security Medical Facility", self.high_security_config_example),
            ("Cost-Optimized Setup", self.cost_optimized_config_example),
            ("Research Environment", self.research_config_example),
            ("Minimal Demo Setup", self.minimal_demo_config_example),
        ]
        
        for name, example_func in examples:
            print(f"\n📋 Example: {name}")
            print("-" * 40)
            example_func()
    
    def development_config_example(self):
        """Example configuration for development environment."""
        print("Setting up development environment configuration...")
        
        # Development-friendly settings
        dev_config = {
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-dev-key-replace-with-real",
            "DEFAULT_MODEL": "gpt-3.5-turbo",  # Cheaper for development
            "COST_LIMIT_DAILY": "50.0",  # Lower limit for dev
            "ENABLE_RESPONSE_CACHE": "true",
            "CACHE_TTL_HOURS": "1",  # Short cache for testing
            "PRESIDIO_ENTITIES": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER",  # Basic set
            "ENABLE_PII_REDACTION": "true",
            "ENABLE_GUARDRAILS": "true",
            "ENABLE_LLAMA_GUARD": "false",  # Disable for faster dev
            "ENABLE_NEMO_GUARDRAILS": "true",
            "JWT_SECRET_KEY": "dev-secret-key-not-for-production",
            "JWT_EXPIRE_MINUTES": "60",  # Short expiry for testing
            "PATIENT_MAX_QUERIES_PER_HOUR": "20",  # Higher for testing
            "PHYSICIAN_MAX_QUERIES_PER_HOUR": "200",
            "ADMIN_MAX_QUERIES_PER_HOUR": "2000",
            "DATABASE_URL": "sqlite:///./dev_medical_chat.db"
        }
        
        self._demonstrate_config(dev_config, "Development")
        
        print("💡 Development Tips:")
        print("  - Use DEBUG=true for detailed logging")
        print("  - Set lower cost limits to avoid unexpected charges")
        print("  - Use shorter JWT expiry for security testing")
        print("  - Enable caching with short TTL for testing cache behavior")
    
    def production_config_example(self):
        """Example configuration for production environment."""
        print("Setting up production environment configuration...")
        
        prod_config = {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-prod-key-from-secrets-manager",
            "DEFAULT_MODEL": "gpt-4",  # Better quality for production
            "HELICONE_API_KEY": "sk-helicone-prod-key",
            "COST_LIMIT_DAILY": "1000.0",
            "COST_ALERT_THRESHOLD": "85.0",
            "ENABLE_RESPONSE_CACHE": "true",
            "CACHE_TTL_HOURS": "24",
            "PRESIDIO_ENTITIES": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD,US_PASSPORT",
            "ENABLE_PII_REDACTION": "true",
            "ENABLE_GUARDRAILS": "true",
            "ENABLE_LLAMA_GUARD": "true",
            "ENABLE_NEMO_GUARDRAILS": "true",
            "ENABLE_MEDICAL_DISCLAIMERS": "true",
            "JWT_SECRET_KEY": "super-secure-production-key-from-vault",
            "JWT_EXPIRE_MINUTES": "480",  # 8 hours
            "PATIENT_MAX_QUERIES_PER_HOUR": "10",
            "PHYSICIAN_MAX_QUERIES_PER_HOUR": "100",
            "ADMIN_MAX_QUERIES_PER_HOUR": "1000",
            "DATABASE_URL": "postgresql://user:pass@prod-db:5432/medical_chat"
        }
        
        self._demonstrate_config(prod_config, "Production")
        
        print("🔒 Production Security Notes:")
        print("  - All security features enabled")
        print("  - Comprehensive PII/PHI entity detection")
        print("  - Strong JWT secret from secure vault")
        print("  - Conservative rate limits")
        print("  - Cost monitoring with alerts")
    
    def high_security_config_example(self):
        """Example configuration for high-security medical facility."""
        print("Setting up high-security medical facility configuration...")
        
        high_sec_config = {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "WARNING",  # Minimal logging for security
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-secure-facility-key",
            "DEFAULT_MODEL": "gpt-4",
            "COST_LIMIT_DAILY": "500.0",
            "ENABLE_RESPONSE_CACHE": "false",  # No caching for max security
            "PRESIDIO_ENTITIES": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD,US_PASSPORT,US_DRIVER_LICENSE,US_BANK_NUMBER,IBAN_CODE,IP_ADDRESS",
            "PRESIDIO_LOG_LEVEL": "ERROR",  # Minimal PII logging
            "ENABLE_PII_REDACTION": "true",
            "ENABLE_GUARDRAILS": "true",
            "ENABLE_LLAMA_GUARD": "true",
            "ENABLE_NEMO_GUARDRAILS": "true",
            "ENABLE_MEDICAL_DISCLAIMERS": "true",
            "JWT_SECRET_KEY": "ultra-secure-facility-key-256-bit",
            "JWT_EXPIRE_MINUTES": "240",  # 4 hours max
            "PATIENT_MAX_QUERIES_PER_HOUR": "5",  # Very restrictive
            "PHYSICIAN_MAX_QUERIES_PER_HOUR": "50",
            "ADMIN_MAX_QUERIES_PER_HOUR": "100",
            "ENABLE_COST_TRACKING": "false",  # Disable external tracking
            "DATABASE_URL": "sqlite:///./secure_facility.db"  # Local only
        }
        
        self._demonstrate_config(high_sec_config, "High Security")
        
        print("🛡️ High Security Features:")
        print("  - Maximum PII/PHI entity detection")
        print("  - No response caching (no data retention)")
        print("  - Minimal logging to reduce data exposure")
        print("  - Very restrictive rate limits")
        print("  - Short JWT expiry")
        print("  - Local database only")
    
    def cost_optimized_config_example(self):
        """Example configuration optimized for cost efficiency."""
        print("Setting up cost-optimized configuration...")
        
        cost_config = {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-cost-optimized-key",
            "DEFAULT_MODEL": "gpt-3.5-turbo",  # Cheaper model
            "MAX_TOKENS": "500",  # Limit response length
            "TEMPERATURE": "0.3",  # Lower temperature for consistency
            "HELICONE_API_KEY": "sk-helicone-cost-tracking",
            "COST_LIMIT_DAILY": "100.0",
            "COST_ALERT_THRESHOLD": "70.0",  # Early warning
            "ENABLE_RESPONSE_CACHE": "true",
            "CACHE_TTL_HOURS": "48",  # Longer cache for cost savings
            "PRESIDIO_ENTITIES": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,MEDICAL_LICENSE",  # Essential only
            "ENABLE_PII_REDACTION": "true",
            "ENABLE_GUARDRAILS": "true",
            "ENABLE_LLAMA_GUARD": "false",  # Disable expensive model
            "ENABLE_NEMO_GUARDRAILS": "true",  # Use rule-based instead
            "JWT_SECRET_KEY": "cost-optimized-secret-key",
            "PATIENT_MAX_QUERIES_PER_HOUR": "8",  # Slightly lower limits
            "PHYSICIAN_MAX_QUERIES_PER_HOUR": "80",
            "ADMIN_MAX_QUERIES_PER_HOUR": "800",
            "DATABASE_URL": "sqlite:///./cost_optimized.db"
        }
        
        self._demonstrate_config(cost_config, "Cost Optimized")
        
        print("💰 Cost Optimization Strategies:")
        print("  - Use GPT-3.5-turbo instead of GPT-4")
        print("  - Limit max tokens to reduce costs")
        print("  - Extended cache TTL for better hit rates")
        print("  - Disable expensive Llama Guard model")
        print("  - Essential PII entities only")
        print("  - Early cost alerts at 70%")
    
    def research_config_example(self):
        """Example configuration for research environment."""
        print("Setting up research environment configuration...")
        
        research_config = {
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-research-key",
            "DEFAULT_MODEL": "gpt-4",  # Best quality for research
            "MAX_TOKENS": "2000",  # Longer responses for analysis
            "TEMPERATURE": "0.1",  # Very consistent for research
            "COST_LIMIT_DAILY": "300.0",  # Higher budget for research
            "ENABLE_RESPONSE_CACHE": "false",  # No cache for fresh responses
            "PRESIDIO_ENTITIES": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,LOCATION",
            "ENABLE_PII_REDACTION": "true",
            "ENABLE_GUARDRAILS": "false",  # Disable for research flexibility
            "ENABLE_LLAMA_GUARD": "false",
            "ENABLE_NEMO_GUARDRAILS": "false",
            "ENABLE_MEDICAL_DISCLAIMERS": "false",  # Research context
            "JWT_SECRET_KEY": "research-environment-key",
            "JWT_EXPIRE_MINUTES": "1440",  # 24 hours for long sessions
            "PATIENT_MAX_QUERIES_PER_HOUR": "100",  # High limits for testing
            "PHYSICIAN_MAX_QUERIES_PER_HOUR": "500",
            "ADMIN_MAX_QUERIES_PER_HOUR": "1000",
            "DATABASE_URL": "sqlite:///./research_data.db"
        }
        
        self._demonstrate_config(research_config, "Research")
        
        print("🔬 Research Environment Features:")
        print("  - GPT-4 for highest quality responses")
        print("  - No response caching for fresh data")
        print("  - Guardrails disabled for flexibility")
        print("  - High rate limits for extensive testing")
        print("  - Long JWT expiry for research sessions")
        print("  - Detailed debug logging")
    
    def minimal_demo_config_example(self):
        """Example minimal configuration for demos and testing."""
        print("Setting up minimal demo configuration...")
        
        demo_config = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-demo-key-replace-me",
            "JWT_SECRET_KEY": "demo-secret-key-not-secure",
            "COST_LIMIT_DAILY": "25.0",  # Very low for demos
            "PRESIDIO_ENTITIES": "PERSON,EMAIL_ADDRESS",  # Minimal set
            "ENABLE_PII_REDACTION": "true",
            "ENABLE_GUARDRAILS": "false",  # Simplified for demos
            "ENABLE_MEDICAL_DISCLAIMERS": "true",
            "PATIENT_MAX_QUERIES_PER_HOUR": "5",
            "PHYSICIAN_MAX_QUERIES_PER_HOUR": "20",
            "ADMIN_MAX_QUERIES_PER_HOUR": "50"
        }
        
        self._demonstrate_config(demo_config, "Minimal Demo")
        
        print("🎯 Demo Configuration Features:")
        print("  - Minimal required settings only")
        print("  - Low cost limits for safety")
        print("  - Basic PII protection")
        print("  - Simplified security for demos")
        print("  - Conservative rate limits")
    
    def _demonstrate_config(self, env_vars: Dict[str, str], config_name: str):
        """Demonstrate a configuration by temporarily setting environment variables."""
        # Save current environment
        original_env = {}
        for key in env_vars:
            original_env[key] = os.environ.get(key)
        
        try:
            # Set new environment variables
            for key, value in env_vars.items():
                os.environ[key] = value
            
            # Load and display configuration
            config_manager = ConfigManager()
            config = config_manager.load_config()
            summary = config_manager.get_config_summary()
            
            print(f"✅ {config_name} configuration loaded successfully!")
            print(f"   Environment: {summary['environment']}")
            print(f"   LLM Provider: {summary['llm']['provider']}")
            print(f"   Default Model: {summary['llm']['default_model']}")
            print(f"   Daily Cost Limit: ${summary['cost']['daily_limit']}")
            print(f"   PII Entities: {len(summary['security']['presidio_entities'])}")
            print(f"   Security Features: PII={summary['security']['enable_pii_redaction']}, "
                  f"Guardrails={summary['security']['enable_guardrails']}")
            
        except Exception as e:
            print(f"❌ Failed to load {config_name} configuration: {str(e)}")
        
        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value


def demonstrate_config_usage():
    """Demonstrate how to use the configuration system in application code."""
    print("\n🔧 Configuration Usage Examples")
    print("=" * 60)
    
    print("\n1. Loading Configuration at Application Startup:")
    print("-" * 50)
    print("""
# In your main.py or app initialization
from src.config import load_config, ConfigurationError

try:
    config = load_config()
    print(f"Application started with {config.environment} configuration")
    print(f"Using {config.llm.provider} with model {config.llm.default_model}")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    sys.exit(1)
""")
    
    print("\n2. Using Configuration in Different Components:")
    print("-" * 50)
    print("""
# In your API endpoints
from src.config import get_config

def chat_endpoint():
    config = get_config()
    
    # Use rate limits based on configuration
    if config.rate_limit.enable_rate_limiting:
        max_queries = config.rate_limit.patient_max_queries_per_hour
        # Apply rate limiting logic
    
    # Use security settings
    if config.security.enable_pii_redaction:
        # Apply PII redaction
        pass
    
    # Use cost settings
    if config.cost.enable_cost_tracking:
        # Track costs with Helicone
        pass
""")
    
    print("\n3. Environment-Specific Configuration:")
    print("-" * 50)
    print("""
# Different .env files for different environments

# .env.development
ENVIRONMENT=development
DEBUG=true
COST_LIMIT_DAILY=50.0
ENABLE_GUARDRAILS=false

# .env.production  
ENVIRONMENT=production
DEBUG=false
COST_LIMIT_DAILY=1000.0
ENABLE_GUARDRAILS=true

# .env.testing
ENVIRONMENT=development
DEBUG=true
COST_LIMIT_DAILY=10.0
ENABLE_PII_REDACTION=false
""")
    
    print("\n4. Configuration Validation:")
    print("-" * 50)
    print("""
# The configuration system automatically validates:
# - Required environment variables are present
# - Values are in correct format (bool, int, float)
# - Enum values are valid (LLM_PROVIDER, ENVIRONMENT, etc.)
# - Production-specific requirements (secure JWT secret)
# - Logical constraints (positive cost limits, rate limits)
""")


def main():
    """Run configuration examples."""
    examples = ConfigExamples()
    examples.run_all_examples()
    
    demonstrate_config_usage()
    
    print("\n🎉 Configuration examples completed!")
    print("\n💡 Next Steps:")
    print("  1. Copy one of the example configurations to your .env file")
    print("  2. Replace placeholder API keys with real values")
    print("  3. Adjust settings based on your specific requirements")
    print("  4. Run the configuration validator to test your setup")
    print("     python src/config_validator.py")


if __name__ == "__main__":
    main()