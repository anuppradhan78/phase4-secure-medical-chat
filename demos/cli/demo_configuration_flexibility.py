#!/usr/bin/env python3
"""
Configuration Flexibility Demonstration

This script demonstrates how the Secure Medical Chat system can be configured
for different environments and use cases through environment variables.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import ConfigManager, ConfigurationError


def demonstrate_configuration_flexibility():
    """Demonstrate different configuration scenarios."""
    print("🎯 Configuration Flexibility Demonstration")
    print("=" * 70)
    print("\nThis demonstration shows how the Secure Medical Chat system")
    print("can be configured for different environments using environment variables.\n")
    
    scenarios = [
        {
            "name": "🏥 High-Security Medical Facility",
            "description": "Maximum security for sensitive medical environments",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-secure-facility-key",
                "JWT_SECRET_KEY": "ultra-secure-facility-key-256-bit",
                "ENVIRONMENT": "production",
                "LOG_LEVEL": "WARNING",
                "ENABLE_PII_REDACTION": "true",
                "ENABLE_GUARDRAILS": "true",
                "ENABLE_LLAMA_GUARD": "true",
                "ENABLE_NEMO_GUARDRAILS": "true",
                "ENABLE_RESPONSE_CACHE": "false",
                "PRESIDIO_ENTITIES": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD,US_PASSPORT",
                "COST_LIMIT_DAILY": "500.0",
                "PATIENT_MAX_QUERIES_PER_HOUR": "5",
                "PHYSICIAN_MAX_QUERIES_PER_HOUR": "50",
                "ADMIN_MAX_QUERIES_PER_HOUR": "100"
            },
            "highlights": [
                "Maximum PII/PHI entity detection (9 entity types)",
                "No response caching (no data retention)",
                "Minimal logging (WARNING level)",
                "Very restrictive rate limits",
                "All security features enabled"
            ]
        },
        {
            "name": "💰 Cost-Optimized Setup",
            "description": "Minimize costs while maintaining essential functionality",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-cost-optimized-key",
                "JWT_SECRET_KEY": "cost-optimized-secret-key",
                "DEFAULT_MODEL": "gpt-3.5-turbo",
                "MAX_TOKENS": "500",
                "TEMPERATURE": "0.3",
                "COST_LIMIT_DAILY": "100.0",
                "COST_ALERT_THRESHOLD": "70.0",
                "ENABLE_RESPONSE_CACHE": "true",
                "CACHE_TTL_HOURS": "48",
                "ENABLE_LLAMA_GUARD": "false",
                "PRESIDIO_ENTITIES": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,MEDICAL_LICENSE",
                "PATIENT_MAX_QUERIES_PER_HOUR": "8",
                "PHYSICIAN_MAX_QUERIES_PER_HOUR": "80"
            },
            "highlights": [
                "Use cheaper GPT-3.5-turbo model",
                "Limit max tokens to 500 (reduces costs)",
                "Extended cache TTL (48 hours)",
                "Disable expensive Llama Guard model",
                "Essential PII entities only (4 types)",
                "Early cost alerts at 70%"
            ]
        },
        {
            "name": "🔬 Research Environment",
            "description": "Research and experimentation with flexibility",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-research-key",
                "JWT_SECRET_KEY": "research-environment-key",
                "ENVIRONMENT": "development",
                "DEBUG": "true",
                "LOG_LEVEL": "DEBUG",
                "DEFAULT_MODEL": "gpt-4",
                "MAX_TOKENS": "2000",
                "TEMPERATURE": "0.1",
                "COST_LIMIT_DAILY": "300.0",
                "ENABLE_GUARDRAILS": "false",
                "ENABLE_RESPONSE_CACHE": "false",
                "ENABLE_MEDICAL_DISCLAIMERS": "false",
                "JWT_EXPIRE_MINUTES": "1440",
                "PATIENT_MAX_QUERIES_PER_HOUR": "100",
                "PHYSICIAN_MAX_QUERIES_PER_HOUR": "500"
            },
            "highlights": [
                "GPT-4 for highest quality responses",
                "No response caching (fresh data)",
                "Guardrails disabled for flexibility",
                "High rate limits for extensive testing",
                "Long JWT expiry (24 hours)",
                "Detailed debug logging"
            ]
        },
        {
            "name": "🚀 Production Environment",
            "description": "Production deployment with balanced security and performance",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-prod-key",
                "JWT_SECRET_KEY": "super-secure-production-key-from-vault",
                "ENVIRONMENT": "production",
                "DEBUG": "false",
                "LOG_LEVEL": "INFO",
                "DEFAULT_MODEL": "gpt-4",
                "HELICONE_API_KEY": "sk-helicone-prod-key",
                "COST_LIMIT_DAILY": "1000.0",
                "COST_ALERT_THRESHOLD": "85.0",
                "ENABLE_RESPONSE_CACHE": "true",
                "CACHE_TTL_HOURS": "24",
                "ENABLE_PII_REDACTION": "true",
                "ENABLE_GUARDRAILS": "true",
                "ENABLE_LLAMA_GUARD": "true",
                "PRESIDIO_ENTITIES": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION",
                "PATIENT_MAX_QUERIES_PER_HOUR": "10",
                "PHYSICIAN_MAX_QUERIES_PER_HOUR": "100"
            },
            "highlights": [
                "All security features enabled",
                "Comprehensive PII/PHI detection (7 types)",
                "Cost monitoring with Helicone",
                "Response caching enabled (24h TTL)",
                "Conservative rate limits",
                "Production-grade JWT secret"
            ]
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{scenario['name']}")
        print("─" * 70)
        print(f"Description: {scenario['description']}\n")
        
        # Save original environment
        original_env = {}
        for key in scenario['env']:
            original_env[key] = os.environ.get(key)
            os.environ[key] = scenario['env'][key]
        
        try:
            # Load configuration
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            # Display configuration summary
            print("✅ Configuration loaded successfully!\n")
            print(f"📊 Configuration Summary:")
            print(f"   Environment:        {config.environment.value}")
            print(f"   LLM Provider:       {config.llm.provider.value}")
            print(f"   Default Model:      {config.llm.default_model}")
            print(f"   Max Tokens:         {config.llm.max_tokens}")
            print(f"   Temperature:        {config.llm.temperature}")
            print(f"   Daily Cost Limit:   ${config.cost.daily_limit}")
            print(f"   Cache Enabled:      {config.cost.enable_response_cache}")
            if config.cost.enable_response_cache:
                print(f"   Cache TTL:          {config.cost.cache_ttl_hours} hours")
            print(f"   PII Redaction:      {config.security.enable_pii_redaction}")
            print(f"   PII Entities:       {len(config.security.presidio_entities)} types")
            print(f"   Guardrails:         {config.security.enable_guardrails}")
            print(f"   Llama Guard:        {config.security.enable_llama_guard}")
            print(f"   Rate Limits:")
            print(f"     - Patient:        {config.rate_limit.patient_max_queries_per_hour}/hour")
            print(f"     - Physician:      {config.rate_limit.physician_max_queries_per_hour}/hour")
            print(f"     - Admin:          {config.rate_limit.admin_max_queries_per_hour}/hour")
            
            # Display highlights
            print(f"\n🎯 Key Features:")
            for highlight in scenario['highlights']:
                print(f"   • {highlight}")
            
        except ConfigurationError as e:
            print(f"❌ Configuration error: {str(e)}")
        
        finally:
            # Restore original environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value
    
    print("\n" + "=" * 70)
    print("🎉 Configuration Flexibility Demonstration Complete!")
    print("\n💡 Key Takeaways:")
    print("   1. Configuration is entirely environment-variable based")
    print("   2. Different scenarios can be configured without code changes")
    print("   3. Security, cost, and performance can be balanced per use case")
    print("   4. Validation ensures configuration correctness on startup")
    print("\n📚 For more information:")
    print("   • See docs/CONFIGURATION_GUIDE.md for detailed scenarios")
    print("   • Run 'python examples/config_examples.py' for more examples")
    print("   • Run 'python src/config_validator.py' to test configurations")


def demonstrate_guardrail_variations():
    """Demonstrate different guardrail configuration options."""
    print("\n\n🛡️  Guardrail Configuration Variations")
    print("=" * 70)
    print("\nDemonstrating how guardrails can be configured for different needs:\n")
    
    variations = [
        {
            "name": "Maximum Protection",
            "env": {
                "ENABLE_GUARDRAILS": "true",
                "ENABLE_LLAMA_GUARD": "true",
                "ENABLE_NEMO_GUARDRAILS": "true"
            },
            "description": "Both Llama Guard and NeMo Guardrails enabled"
        },
        {
            "name": "NeMo Only (Rule-Based)",
            "env": {
                "ENABLE_GUARDRAILS": "true",
                "ENABLE_LLAMA_GUARD": "false",
                "ENABLE_NEMO_GUARDRAILS": "true"
            },
            "description": "Rule-based guardrails only (faster, lower cost)"
        },
        {
            "name": "Llama Guard Only (ML-Based)",
            "env": {
                "ENABLE_GUARDRAILS": "true",
                "ENABLE_LLAMA_GUARD": "true",
                "ENABLE_NEMO_GUARDRAILS": "false"
            },
            "description": "ML-based safety classifier only (more comprehensive)"
        },
        {
            "name": "Guardrails Disabled",
            "env": {
                "ENABLE_GUARDRAILS": "false",
                "ENABLE_LLAMA_GUARD": "false",
                "ENABLE_NEMO_GUARDRAILS": "false"
            },
            "description": "No guardrails (for research/testing only)"
        }
    ]
    
    base_env = {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test-key",
        "JWT_SECRET_KEY": "test-secret"
    }
    
    for variation in variations:
        print(f"📋 {variation['name']}")
        print(f"   {variation['description']}")
        
        # Combine base and variation env
        test_env = {**base_env, **variation['env']}
        
        # Save and set environment
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]
        
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            print(f"   ✅ Guardrails: {config.security.enable_guardrails}, "
                  f"Llama Guard: {config.security.enable_llama_guard}, "
                  f"NeMo: {config.security.enable_nemo_guardrails}\n")
        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}\n")
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value


def demonstrate_cost_monitoring():
    """Demonstrate cost monitoring configuration options."""
    print("\n\n💰 Cost Monitoring Configuration")
    print("=" * 70)
    print("\nDemonstrating how cost limits and monitoring can be configured:\n")
    
    cost_configs = [
        {
            "name": "Conservative (Low Budget)",
            "daily_limit": "50.0",
            "alert_threshold": "70.0",
            "description": "Early alerts, low daily limit"
        },
        {
            "name": "Standard (Medium Budget)",
            "daily_limit": "200.0",
            "alert_threshold": "80.0",
            "description": "Balanced monitoring"
        },
        {
            "name": "Enterprise (High Budget)",
            "daily_limit": "1000.0",
            "alert_threshold": "90.0",
            "description": "High limit, late alerts"
        }
    ]
    
    base_env = {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test-key",
        "JWT_SECRET_KEY": "test-secret"
    }
    
    for cost_config in cost_configs:
        print(f"📊 {cost_config['name']}")
        print(f"   {cost_config['description']}")
        
        test_env = {
            **base_env,
            "COST_LIMIT_DAILY": cost_config['daily_limit'],
            "COST_ALERT_THRESHOLD": cost_config['alert_threshold']
        }
        
        # Save and set environment
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]
        
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            alert_amount = config.cost.daily_limit * (config.cost.cost_alert_threshold / 100)
            print(f"   Daily Limit: ${config.cost.daily_limit}")
            print(f"   Alert Threshold: {config.cost.cost_alert_threshold}%")
            print(f"   Alert triggers at: ${alert_amount:.2f}\n")
        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}\n")
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value


if __name__ == "__main__":
    demonstrate_configuration_flexibility()
    demonstrate_guardrail_variations()
    demonstrate_cost_monitoring()
    
    print("\n" + "=" * 70)
    print("✨ All demonstrations completed successfully!")
    print("\n📖 Next Steps:")
    print("   1. Review docs/CONFIGURATION_GUIDE.md for complete documentation")
    print("   2. Copy .env.example to .env and customize for your needs")
    print("   3. Run 'python src/startup_config.py' to validate your configuration")
    print("   4. Start the application with 'python -m src.main'")
