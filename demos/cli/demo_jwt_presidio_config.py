#!/usr/bin/env python3
"""
JWT_SECRET_KEY and PRESIDIO_ENTITIES Configuration Demonstration

This script demonstrates how JWT_SECRET_KEY and PRESIDIO_ENTITIES environment
variables are validated and configured in different scenarios.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import ConfigManager, ConfigurationError


def demonstrate_jwt_secret_validation():
    """Demonstrate JWT_SECRET_KEY validation in different environments."""
    print("🔐 JWT_SECRET_KEY Configuration Demonstration")
    print("=" * 70)
    print("\nDemonstrating JWT secret key validation for different environments:\n")
    
    scenarios = [
        {
            "name": "❌ Default JWT Secret in Production",
            "description": "Should fail validation in production environment",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-test-key",
                "JWT_SECRET_KEY": "your-super-secret-jwt-key-change-this-in-production",
                "ENVIRONMENT": "production"
            },
            "should_fail": True
        },
        {
            "name": "⚠️  Default JWT Secret in Development",
            "description": "Should warn but allow in development environment",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-test-key",
                "JWT_SECRET_KEY": "your-super-secret-jwt-key-change-this-in-production",
                "ENVIRONMENT": "development"
            },
            "should_fail": False
        },
        {
            "name": "⚠️  Short JWT Secret",
            "description": "Should warn about short key length",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-test-key",
                "JWT_SECRET_KEY": "short-key",
                "ENVIRONMENT": "development"
            },
            "should_fail": False
        },
        {
            "name": "✅ Secure JWT Secret in Production",
            "description": "Should pass validation with secure key",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-test-key",
                "JWT_SECRET_KEY": "super-secure-production-key-with-sufficient-length-for-security",
                "ENVIRONMENT": "production"
            },
            "should_fail": False
        },
        {
            "name": "✅ Custom JWT Secret in Development",
            "description": "Should pass validation with custom key",
            "env": {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "sk-test-key",
                "JWT_SECRET_KEY": "custom-development-secret-key-for-testing-purposes",
                "ENVIRONMENT": "development"
            },
            "should_fail": False
        }
    ]
    
    for scenario in scenarios:
        print(f"{scenario['name']}")
        print(f"   {scenario['description']}")
        
        # Save and set environment
        original_env = {}
        for key in scenario['env']:
            original_env[key] = os.environ.get(key)
            os.environ[key] = scenario['env'][key]
        
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            if scenario['should_fail']:
                print("   ❌ UNEXPECTED: Configuration should have failed but passed")
            else:
                print(f"   ✅ JWT Secret: '{config.auth.jwt_secret_key[:20]}...' (length: {len(config.auth.jwt_secret_key)})")
                print(f"   Environment: {config.environment.value}")
                print(f"   Algorithm: {config.auth.jwt_algorithm}")
                print(f"   Expiry: {config.auth.jwt_expire_minutes} minutes")
        
        except ConfigurationError as e:
            if scenario['should_fail']:
                print(f"   ✅ EXPECTED FAILURE: {str(e)}")
            else:
                print(f"   ❌ UNEXPECTED FAILURE: {str(e)}")
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value
        
        print()


def demonstrate_presidio_entities_configuration():
    """Demonstrate PRESIDIO_ENTITIES configuration options."""
    print("\n🔍 PRESIDIO_ENTITIES Configuration Demonstration")
    print("=" * 70)
    print("\nDemonstrating different PII/PHI entity detection configurations:\n")
    
    scenarios = [
        {
            "name": "🏥 Maximum Medical Security",
            "description": "Comprehensive PII/PHI detection for medical facilities",
            "entities": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD,US_PASSPORT,US_DRIVER_LICENSE,US_BANK_NUMBER,IBAN_CODE,IP_ADDRESS"
        },
        {
            "name": "🏢 Standard Healthcare",
            "description": "Standard PII/PHI detection for healthcare applications",
            "entities": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION"
        },
        {
            "name": "💰 Cost-Optimized",
            "description": "Essential PII detection only to minimize processing costs",
            "entities": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,MEDICAL_LICENSE"
        },
        {
            "name": "🔬 Research Environment",
            "description": "Balanced detection for research with patient data",
            "entities": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,LOCATION"
        },
        {
            "name": "🎯 Minimal Demo",
            "description": "Basic detection for demonstrations and testing",
            "entities": "PERSON,EMAIL_ADDRESS"
        },
        {
            "name": "❌ Empty Entities (Should Fail)",
            "description": "Empty entity list should fail validation",
            "entities": "",
            "should_fail": True
        }
    ]
    
    base_env = {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test-key",
        "JWT_SECRET_KEY": "test-secret-key-for-presidio-demo"
    }
    
    for scenario in scenarios:
        print(f"{scenario['name']}")
        print(f"   {scenario['description']}")
        
        test_env = {
            **base_env,
            "PRESIDIO_ENTITIES": scenario['entities']
        }
        
        # Save and set environment
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]
        
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            if scenario.get('should_fail', False):
                print("   ❌ UNEXPECTED: Configuration should have failed but passed")
            else:
                entities = config.security.presidio_entities
                print(f"   ✅ Entity Count: {len(entities)}")
                print(f"   Entities: {', '.join(entities)}")
                print(f"   PII Redaction Enabled: {config.security.enable_pii_redaction}")
        
        except ConfigurationError as e:
            if scenario.get('should_fail', False):
                print(f"   ✅ EXPECTED FAILURE: {str(e)}")
            else:
                print(f"   ❌ UNEXPECTED FAILURE: {str(e)}")
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value
        
        print()


def demonstrate_configuration_combinations():
    """Demonstrate different combinations of JWT and Presidio configurations."""
    print("\n🔧 Configuration Combinations Demonstration")
    print("=" * 70)
    print("\nDemonstrating how JWT_SECRET_KEY and PRESIDIO_ENTITIES work together:\n")
    
    combinations = [
        {
            "name": "🏥 High-Security Medical Facility",
            "jwt_secret": "ultra-secure-medical-facility-jwt-key-256-bit-encryption",
            "entities": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD,US_PASSPORT,US_DRIVER_LICENSE",
            "environment": "production",
            "jwt_expiry": "240"  # 4 hours
        },
        {
            "name": "🚀 Production Healthcare",
            "jwt_secret": "production-healthcare-jwt-secret-from-vault",
            "entities": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION",
            "environment": "production",
            "jwt_expiry": "480"  # 8 hours
        },
        {
            "name": "🔬 Research Environment",
            "jwt_secret": "research-environment-jwt-key-for-long-sessions",
            "entities": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,LOCATION",
            "environment": "development",
            "jwt_expiry": "1440"  # 24 hours
        },
        {
            "name": "💰 Cost-Optimized Setup",
            "jwt_secret": "cost-optimized-jwt-secret-key",
            "entities": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,MEDICAL_LICENSE",
            "environment": "production",
            "jwt_expiry": "720"  # 12 hours
        }
    ]
    
    base_env = {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test-key"
    }
    
    for combination in combinations:
        print(f"{combination['name']}")
        
        test_env = {
            **base_env,
            "JWT_SECRET_KEY": combination['jwt_secret'],
            "PRESIDIO_ENTITIES": combination['entities'],
            "ENVIRONMENT": combination['environment'],
            "JWT_EXPIRE_MINUTES": combination['jwt_expiry']
        }
        
        # Save and set environment
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]
        
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            print(f"   ✅ Configuration loaded successfully!")
            print(f"   Environment: {config.environment.value}")
            print(f"   JWT Secret Length: {len(config.auth.jwt_secret_key)} characters")
            print(f"   JWT Expiry: {config.auth.jwt_expire_minutes} minutes ({config.auth.jwt_expire_minutes/60:.1f} hours)")
            print(f"   PII Entities: {len(config.security.presidio_entities)} types")
            print(f"   Entity Types: {', '.join(config.security.presidio_entities[:3])}{'...' if len(config.security.presidio_entities) > 3 else ''}")
            
            # Calculate security score
            security_score = sum([
                config.security.enable_pii_redaction,
                config.security.enable_guardrails,
                config.security.enable_medical_disclaimers,
                len(config.auth.jwt_secret_key) >= 32,  # Secure JWT length
                len(config.security.presidio_entities) >= 5  # Comprehensive PII detection
            ])
            print(f"   Security Score: {security_score}/5")
        
        except ConfigurationError as e:
            print(f"   ❌ Configuration error: {str(e)}")
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value
        
        print()


def demonstrate_validation_rules():
    """Demonstrate the validation rules for JWT and Presidio configuration."""
    print("\n📋 Configuration Validation Rules")
    print("=" * 70)
    print("\nValidation rules for JWT_SECRET_KEY and PRESIDIO_ENTITIES:\n")
    
    print("🔐 JWT_SECRET_KEY Validation Rules:")
    print("   1. ✅ REQUIRED: Must be set (cannot be empty)")
    print("   2. ⚠️  PRODUCTION: Cannot use default value in production environment")
    print("   3. ⚠️  LENGTH: Should be at least 32 characters for security")
    print("   4. ✅ FORMAT: Any string format is accepted")
    print("   5. 🔒 SECURITY: Longer keys provide better security")
    
    print("\n🔍 PRESIDIO_ENTITIES Validation Rules:")
    print("   1. ✅ REQUIRED: Cannot be empty (must detect at least one entity type)")
    print("   2. ✅ FORMAT: Comma-separated list of entity names")
    print("   3. ✅ CASE: Entity names are case-sensitive (use uppercase)")
    print("   4. ⚠️  COVERAGE: More entities provide better PII/PHI protection")
    print("   5. 💰 COST: More entities increase processing time and costs")
    
    print("\n📊 Common Entity Types:")
    entity_categories = {
        "Personal Information": [
            "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "LOCATION", "IP_ADDRESS"
        ],
        "Medical Information": [
            "MEDICAL_LICENSE", "US_SSN", "DATE_TIME"
        ],
        "Financial Information": [
            "CREDIT_CARD", "US_BANK_NUMBER", "IBAN_CODE"
        ],
        "Government IDs": [
            "US_PASSPORT", "US_DRIVER_LICENSE"
        ]
    }
    
    for category, entities in entity_categories.items():
        print(f"\n   {category}:")
        for entity in entities:
            print(f"     • {entity}")
    
    print("\n💡 Configuration Tips:")
    print("   • Use environment-specific .env files (.env.development, .env.production)")
    print("   • Store production JWT secrets in secure vaults (not in .env files)")
    print("   • Choose entity types based on your specific use case and data")
    print("   • Test configurations with 'python src/config_validator.py'")
    print("   • Monitor costs when using many entity types")


if __name__ == "__main__":
    demonstrate_jwt_secret_validation()
    demonstrate_presidio_entities_configuration()
    demonstrate_configuration_combinations()
    demonstrate_validation_rules()
    
    print("\n" + "=" * 70)
    print("✨ JWT_SECRET_KEY and PRESIDIO_ENTITIES demonstration completed!")
    print("\n📖 Key Takeaways:")
    print("   1. JWT_SECRET_KEY must be secure in production environments")
    print("   2. PRESIDIO_ENTITIES controls PII/PHI detection comprehensiveness")
    print("   3. Both variables are validated on application startup")
    print("   4. Configuration flexibility allows different security levels")
    print("   5. Validation prevents common security misconfigurations")