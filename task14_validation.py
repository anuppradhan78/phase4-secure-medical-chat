#!/usr/bin/env python3
"""
Task 14 Validation: Environment-Based Configuration

This script validates that all requirements for Task 14 are implemented:
- Read configuration from environment variables: LLM_PROVIDER, HELICONE_API_KEY, PRESIDIO_ENTITIES
- Demonstrate different guardrail settings through configuration
- Show how to configure cost limits and monitoring thresholds
- Validate required configuration on startup with clear error messages
- Demonstrate configuration flexibility through examples
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import ConfigManager, ConfigurationError


def validate_task_14_requirements():
    """Validate all Task 14 requirements are implemented."""
    print("✅ Task 14 Validation: Environment-Based Configuration")
    print("=" * 80)
    print("\nValidating all requirements from Task 14...\n")
    
    requirements = [
        {
            "id": "11.1",
            "description": "Read configuration from environment variables: LLM_PROVIDER, HELICONE_API_KEY, PRESIDIO_ENTITIES",
            "test": test_environment_variable_reading
        },
        {
            "id": "11.2", 
            "description": "Demonstrate different guardrail settings through configuration",
            "test": test_guardrail_configuration
        },
        {
            "id": "11.3",
            "description": "Show how to configure cost limits and monitoring thresholds",
            "test": test_cost_configuration
        },
        {
            "id": "11.4",
            "description": "Validate required configuration on startup with clear error messages",
            "test": test_startup_validation
        },
        {
            "id": "11.5",
            "description": "Demonstrate configuration flexibility through examples",
            "test": test_configuration_flexibility
        }
    ]
    
    passed = 0
    failed = 0
    
    for req in requirements:
        print(f"📋 Requirement {req['id']}: {req['description']}")
        print("-" * 80)
        
        try:
            result = req['test']()
            if result:
                print(f"✅ PASSED: Requirement {req['id']}")
                passed += 1
            else:
                print(f"❌ FAILED: Requirement {req['id']}")
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: Requirement {req['id']} - {str(e)}")
            failed += 1
        
        print()
    
    print("=" * 80)
    print(f"📊 TASK 14 VALIDATION SUMMARY")
    print("=" * 80)
    print(f"Total Requirements: {len(requirements)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(requirements)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TASK 14 REQUIREMENTS PASSED!")
        print("✅ Environment-based configuration is fully implemented")
    else:
        print(f"\n⚠️  {failed} requirements failed. Please review the implementation.")
    
    return failed == 0


def test_environment_variable_reading():
    """Test reading configuration from environment variables."""
    print("Testing environment variable reading...")
    
    # Test LLM_PROVIDER
    test_env = {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test-key",
        "JWT_SECRET_KEY": "test-secret",
        "HELICONE_API_KEY": "sk-helicone-test",
        "PRESIDIO_ENTITIES": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,MEDICAL_LICENSE"
    }
    
    original_env = {}
    for key in test_env:
        original_env[key] = os.environ.get(key)
        os.environ[key] = test_env[key]
    
    try:
        config_manager = ConfigManager()
        config = config_manager.load_config()
        
        # Verify LLM_PROVIDER is read correctly
        assert config.llm.provider.value == "openai", f"Expected openai, got {config.llm.provider.value}"
        print("   ✅ LLM_PROVIDER read correctly")
        
        # Verify HELICONE_API_KEY is read correctly
        assert config.cost.helicone_api_key == "sk-helicone-test", "HELICONE_API_KEY not read correctly"
        print("   ✅ HELICONE_API_KEY read correctly")
        
        # Verify PRESIDIO_ENTITIES is read correctly
        expected_entities = ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "MEDICAL_LICENSE"]
        assert config.security.presidio_entities == expected_entities, f"Expected {expected_entities}, got {config.security.presidio_entities}"
        print("   ✅ PRESIDIO_ENTITIES read correctly")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return False
    
    finally:
        # Restore environment
        for key, original_value in original_env.items():
            if original_value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = original_value


def test_guardrail_configuration():
    """Test different guardrail settings through configuration."""
    print("Testing guardrail configuration options...")
    
    guardrail_configs = [
        {
            "name": "Both Enabled",
            "env": {"ENABLE_LLAMA_GUARD": "true", "ENABLE_NEMO_GUARDRAILS": "true"},
            "expected": (True, True)
        },
        {
            "name": "NeMo Only",
            "env": {"ENABLE_LLAMA_GUARD": "false", "ENABLE_NEMO_GUARDRAILS": "true"},
            "expected": (False, True)
        },
        {
            "name": "Llama Guard Only",
            "env": {"ENABLE_LLAMA_GUARD": "true", "ENABLE_NEMO_GUARDRAILS": "false"},
            "expected": (True, False)
        },
        {
            "name": "Both Disabled",
            "env": {"ENABLE_LLAMA_GUARD": "false", "ENABLE_NEMO_GUARDRAILS": "false"},
            "expected": (False, False)
        }
    ]
    
    base_env = {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test-key",
        "JWT_SECRET_KEY": "test-secret"
    }
    
    for config_test in guardrail_configs:
        test_env = {**base_env, **config_test['env']}
        
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]
        
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            expected_llama, expected_nemo = config_test['expected']
            actual_llama = config.security.enable_llama_guard
            actual_nemo = config.security.enable_nemo_guardrails
            
            assert actual_llama == expected_llama, f"Llama Guard: expected {expected_llama}, got {actual_llama}"
            assert actual_nemo == expected_nemo, f"NeMo: expected {expected_nemo}, got {actual_nemo}"
            
            print(f"   ✅ {config_test['name']}: Llama Guard={actual_llama}, NeMo={actual_nemo}")
            
        except Exception as e:
            print(f"   ❌ {config_test['name']}: {str(e)}")
            return False
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value
    
    return True


def test_cost_configuration():
    """Test cost limits and monitoring threshold configuration."""
    print("Testing cost configuration options...")
    
    cost_configs = [
        {"daily_limit": "50.0", "alert_threshold": "70.0"},
        {"daily_limit": "200.0", "alert_threshold": "80.0"},
        {"daily_limit": "1000.0", "alert_threshold": "90.0"}
    ]
    
    base_env = {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test-key",
        "JWT_SECRET_KEY": "test-secret"
    }
    
    for cost_config in cost_configs:
        test_env = {
            **base_env,
            "COST_LIMIT_DAILY": cost_config['daily_limit'],
            "COST_ALERT_THRESHOLD": cost_config['alert_threshold']
        }
        
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]
        
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            expected_limit = float(cost_config['daily_limit'])
            expected_threshold = float(cost_config['alert_threshold'])
            
            assert config.cost.daily_limit == expected_limit, f"Daily limit: expected {expected_limit}, got {config.cost.daily_limit}"
            assert config.cost.cost_alert_threshold == expected_threshold, f"Alert threshold: expected {expected_threshold}, got {config.cost.cost_alert_threshold}"
            
            alert_amount = config.cost.daily_limit * (config.cost.cost_alert_threshold / 100)
            print(f"   ✅ Daily Limit: ${config.cost.daily_limit}, Alert at: ${alert_amount:.2f}")
            
        except Exception as e:
            print(f"   ❌ Cost config error: {str(e)}")
            return False
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value
    
    return True


def test_startup_validation():
    """Test startup validation with clear error messages."""
    print("Testing startup validation and error messages...")
    
    # Test missing required variable
    original_env = {}
    required_vars = ["LLM_PROVIDER", "OPENAI_API_KEY", "JWT_SECRET_KEY"]
    
    for var in required_vars:
        original_env[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    try:
        config_manager = ConfigManager()
        config_manager.load_config()
        print("   ❌ Should have failed with missing required variables")
        return False
    except ConfigurationError as e:
        error_msg = str(e)
        if "Required environment variable" in error_msg:
            print(f"   ✅ Clear error message for missing variable: {error_msg}")
        else:
            print(f"   ❌ Error message not clear enough: {error_msg}")
            return False
    finally:
        # Restore environment
        for key, original_value in original_env.items():
            if original_value is not None:
                os.environ[key] = original_value
    
    # Test invalid LLM provider
    test_env = {
        "LLM_PROVIDER": "invalid_provider",
        "OPENAI_API_KEY": "sk-test-key",
        "JWT_SECRET_KEY": "test-secret"
    }
    
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        config_manager = ConfigManager()
        config_manager.load_config()
        print("   ❌ Should have failed with invalid LLM provider")
        return False
    except ConfigurationError as e:
        error_msg = str(e)
        if "Invalid LLM_PROVIDER" in error_msg:
            print(f"   ✅ Clear error message for invalid provider: {error_msg}")
        else:
            print(f"   ❌ Error message not clear enough: {error_msg}")
            return False
    finally:
        # Restore environment
        for key, original_value in original_env.items():
            if original_value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = original_value
    
    return True


def test_configuration_flexibility():
    """Test configuration flexibility through different examples."""
    print("Testing configuration flexibility...")
    
    scenarios = [
        {
            "name": "Development",
            "env": {
                "ENVIRONMENT": "development",
                "DEBUG": "true",
                "COST_LIMIT_DAILY": "50.0",
                "ENABLE_LLAMA_GUARD": "false"
            }
        },
        {
            "name": "Production",
            "env": {
                "ENVIRONMENT": "production",
                "DEBUG": "false",
                "COST_LIMIT_DAILY": "1000.0",
                "ENABLE_LLAMA_GUARD": "true"
            }
        },
        {
            "name": "High Security",
            "env": {
                "ENVIRONMENT": "production",
                "PRESIDIO_ENTITIES": "PERSON,DATE_TIME,PHONE_NUMBER,EMAIL_ADDRESS,MEDICAL_LICENSE,US_SSN,LOCATION,CREDIT_CARD",
                "ENABLE_RESPONSE_CACHE": "false",
                "PATIENT_MAX_QUERIES_PER_HOUR": "5"
            }
        }
    ]
    
    base_env = {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test-key",
        "JWT_SECRET_KEY": "test-secret-for-flexibility-test"
    }
    
    for scenario in scenarios:
        test_env = {**base_env, **scenario['env']}
        
        original_env = {}
        for key in test_env:
            original_env[key] = os.environ.get(key)
            os.environ[key] = test_env[key]
        
        try:
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            print(f"   ✅ {scenario['name']}: Environment={config.environment.value}, "
                  f"Cost Limit=${config.cost.daily_limit}, "
                  f"PII Entities={len(config.security.presidio_entities)}")
            
        except Exception as e:
            print(f"   ❌ {scenario['name']}: {str(e)}")
            return False
        
        finally:
            # Restore environment
            for key, original_value in original_env.items():
                if original_value is None:
                    if key in os.environ:
                        del os.environ[key]
                else:
                    os.environ[key] = original_value
    
    return True


if __name__ == "__main__":
    success = validate_task_14_requirements()
    
    print("\n" + "=" * 80)
    print("📚 ADDITIONAL RESOURCES")
    print("=" * 80)
    print("Configuration documentation and examples:")
    print("  • docs/CONFIGURATION_GUIDE.md - Complete configuration guide")
    print("  • .env.example - Example configuration file")
    print("  • examples/config_examples.py - Configuration examples")
    print("  • src/config_validator.py - Configuration validation tests")
    print("  • demo_configuration_flexibility.py - Flexibility demonstration")
    print("  • demo_jwt_presidio_config.py - JWT and Presidio configuration demo")
    
    print("\nValidation commands:")
    print("  • python src/startup_config.py - Validate current configuration")
    print("  • python src/config_validator.py - Run all configuration tests")
    print("  • python examples/config_examples.py - See configuration examples")
    
    sys.exit(0 if success else 1)