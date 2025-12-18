#!/usr/bin/env python3
"""
Configuration Testing Script

This script demonstrates and tests the environment-based configuration system
for the Secure Medical Chat application.
"""

import os
import sys
import json
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_configuration_system():
    """Test the configuration system with various scenarios."""
    print("🧪 Testing Secure Medical Chat Configuration System")
    print("=" * 60)
    
    # Test 1: Run configuration validator
    print("\n1️⃣  Running Configuration Validator...")
    print("-" * 40)
    
    try:
        from src.config_validator import ConfigValidator
        validator = ConfigValidator()
        results = validator.run_validation_tests()
        
        if results["summary"]["failed"] == 0:
            print("✅ All configuration validation tests passed!")
        else:
            print(f"⚠️  {results['summary']['failed']} validation tests failed")
            
    except Exception as e:
        print(f"❌ Configuration validator error: {str(e)}")
    
    # Test 2: Test startup configuration
    print("\n2️⃣  Testing Startup Configuration...")
    print("-" * 40)
    
    try:
        from src.startup_config import validate_startup_configuration
        
        # Set minimal test environment
        test_env = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test-key-for-demo",
            "JWT_SECRET_KEY": "test-secret-key-for-demo"
        }
        
        # Save original environment
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]
        
        try:
            success, config = validate_startup_configuration()
            if success:
                print("✅ Startup configuration validation passed!")
                print(f"   Environment: {config.environment.value}")
                print(f"   LLM Provider: {config.llm.provider.value}")
                print(f"   Security Features: {sum([config.security.enable_pii_redaction, config.security.enable_guardrails, config.security.enable_medical_disclaimers])}/3")
            else:
                print("❌ Startup configuration validation failed")
        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value
                    
    except Exception as e:
        print(f"❌ Startup configuration error: {str(e)}")
    
    # Test 3: Run configuration examples
    print("\n3️⃣  Running Configuration Examples...")
    print("-" * 40)
    
    try:
        from examples.config_examples import ConfigExamples
        examples = ConfigExamples()
        examples.run_all_examples()
        print("✅ Configuration examples completed successfully!")
        
    except Exception as e:
        print(f"❌ Configuration examples error: {str(e)}")
    
    # Test 4: Test configuration flexibility
    print("\n4️⃣  Testing Configuration Flexibility...")
    print("-" * 40)
    
    test_scenarios = [
        {
            "name": "High Security Medical Facility",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-secure-facility",
                "JWT_SECRET_KEY": "ultra-secure-facility-key",
                "ENVIRONMENT": "production",
                "ENABLE_PII_REDACTION": "true",
                "ENABLE_GUARDRAILS": "true",
                "ENABLE_LLAMA_GUARD": "true",
                "ENABLE_NEMO_GUARDRAILS": "true",
                "PRESIDIO_ENTITIES": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD",
                "COST_LIMIT_DAILY": "500.0",
                "PATIENT_MAX_QUERIES_PER_HOUR": "5",
                "PHYSICIAN_MAX_QUERIES_PER_HOUR": "50",
                "ADMIN_MAX_QUERIES_PER_HOUR": "100"
            }
        },
        {
            "name": "Cost-Optimized Setup",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-cost-optimized",
                "JWT_SECRET_KEY": "cost-optimized-key",
                "DEFAULT_MODEL": "gpt-3.5-turbo",
                "MAX_TOKENS": "500",
                "COST_LIMIT_DAILY": "50.0",
                "ENABLE_RESPONSE_CACHE": "true",
                "CACHE_TTL_HOURS": "48",
                "ENABLE_LLAMA_GUARD": "false",
                "PRESIDIO_ENTITIES": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER"
            }
        },
        {
            "name": "Research Environment",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-research-key",
                "JWT_SECRET_KEY": "research-key",
                "ENVIRONMENT": "development",
                "DEBUG": "true",
                "DEFAULT_MODEL": "gpt-4",
                "MAX_TOKENS": "2000",
                "COST_LIMIT_DAILY": "300.0",
                "ENABLE_GUARDRAILS": "false",
                "ENABLE_RESPONSE_CACHE": "false",
                "PATIENT_MAX_QUERIES_PER_HOUR": "100",
                "PHYSICIAN_MAX_QUERIES_PER_HOUR": "500"
            }
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n   Testing: {scenario['name']}")
        
        # Save and set environment
        original_env = {}
        for key in scenario['env']:
            original_env[key] = os.environ.get(key)
            os.environ[key] = scenario['env'][key]
        
        try:
            from src.config import ConfigManager
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            print(f"   ✅ {scenario['name']}: Configuration loaded successfully")
            print(f"      Environment: {config.environment.value}")
            print(f"      Model: {config.llm.default_model}")
            print(f"      Cost Limit: ${config.cost.daily_limit}")
            print(f"      Security Score: {sum([config.security.enable_pii_redaction, config.security.enable_guardrails, config.security.enable_medical_disclaimers])}/3")
            
        except Exception as e:
            print(f"   ❌ {scenario['name']}: {str(e)}")
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value
    
    print("\n" + "=" * 60)
    print("🎉 Configuration System Testing Completed!")
    print("\n💡 Next Steps:")
    print("  1. Set up your .env file with appropriate values")
    print("  2. Run 'python src/startup_config.py' to validate your configuration")
    print("  3. Start the application with 'python -m src.main'")
    print("  4. Check /api/config endpoint for runtime configuration info")


def demonstrate_environment_variables():
    """Demonstrate the environment variables used by the system."""
    print("\n📋 Environment Variables Reference")
    print("=" * 60)
    
    env_vars = {
        "Core Configuration": {
            "LLM_PROVIDER": "openai (required) - LLM provider to use",
            "OPENAI_API_KEY": "sk-... (required) - OpenAI API key",
            "JWT_SECRET_KEY": "(required) - Secret key for JWT tokens",
            "ENVIRONMENT": "development|staging|production - Application environment",
            "DEBUG": "true|false - Enable debug mode",
            "LOG_LEVEL": "DEBUG|INFO|WARNING|ERROR - Logging level"
        },
        "Cost Management": {
            "HELICONE_API_KEY": "sk-helicone-... - Helicone proxy API key",
            "COST_LIMIT_DAILY": "100.0 - Daily cost limit in USD",
            "COST_ALERT_THRESHOLD": "80.0 - Alert threshold percentage",
            "ENABLE_RESPONSE_CACHE": "true|false - Enable response caching",
            "CACHE_TTL_HOURS": "24 - Cache time-to-live in hours"
        },
        "Security & Privacy": {
            "PRESIDIO_ENTITIES": "PERSON,EMAIL_ADDRESS,... - PII entities to detect",
            "ENABLE_PII_REDACTION": "true|false - Enable PII redaction",
            "ENABLE_GUARDRAILS": "true|false - Enable guardrails",
            "ENABLE_LLAMA_GUARD": "true|false - Enable Llama Guard",
            "ENABLE_NEMO_GUARDRAILS": "true|false - Enable NeMo Guardrails",
            "GUARDRAILS_CONFIG_PATH": "config/guardrails - Path to guardrails config"
        },
        "Rate Limiting": {
            "PATIENT_MAX_QUERIES_PER_HOUR": "10 - Patient rate limit",
            "PHYSICIAN_MAX_QUERIES_PER_HOUR": "100 - Physician rate limit", 
            "ADMIN_MAX_QUERIES_PER_HOUR": "1000 - Admin rate limit",
            "ENABLE_RATE_LIMITING": "true|false - Enable rate limiting"
        },
        "LLM Settings": {
            "DEFAULT_MODEL": "gpt-3.5-turbo - Default LLM model",
            "MAX_TOKENS": "1000 - Maximum tokens per response",
            "TEMPERATURE": "0.7 - LLM temperature setting"
        },
        "Database": {
            "DATABASE_URL": "sqlite:///./secure_chat.db - Database connection URL"
        }
    }
    
    for category, vars_dict in env_vars.items():
        print(f"\n{category}:")
        print("-" * len(category))
        for var_name, description in vars_dict.items():
            print(f"  {var_name:<30} {description}")


if __name__ == "__main__":
    test_configuration_system()
    demonstrate_environment_variables()