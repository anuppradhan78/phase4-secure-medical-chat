"""
Configuration validation and demonstration script.

This script demonstrates different configuration scenarios and validates
that the configuration system works correctly with various settings.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import ConfigManager, ConfigurationError, Environment, LLMProvider, LogLevel


class ConfigValidator:
    """Validates and demonstrates configuration scenarios."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.test_results: List[Dict[str, Any]] = []
    
    def run_validation_tests(self) -> Dict[str, Any]:
        """Run comprehensive configuration validation tests."""
        print("🔧 Running Configuration Validation Tests...")
        print("=" * 60)
        
        # Test scenarios
        scenarios = [
            ("Minimal Configuration", self._test_minimal_config),
            ("Full Configuration", self._test_full_config),
            ("Production Configuration", self._test_production_config),
            ("Invalid Configuration", self._test_invalid_config),
            ("Missing Required Variables", self._test_missing_required),
            ("Different Guardrail Settings", self._test_guardrail_variations),
            ("Cost Limit Variations", self._test_cost_variations),
            ("Security Feature Toggles", self._test_security_toggles),
        ]
        
        for scenario_name, test_func in scenarios:
            print(f"\n📋 Testing: {scenario_name}")
            print("-" * 40)
            
            try:
                result = test_func()
                self.test_results.append({
                    "scenario": scenario_name,
                    "status": "PASS",
                    "details": result
                })
                print(f"✅ {scenario_name}: PASSED")
                
            except Exception as e:
                self.test_results.append({
                    "scenario": scenario_name,
                    "status": "FAIL",
                    "error": str(e)
                })
                print(f"❌ {scenario_name}: FAILED - {str(e)}")
        
        # Generate summary
        summary = self._generate_summary()
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        
        return {
            "summary": summary,
            "results": self.test_results
        }
    
    def _test_minimal_config(self) -> Dict[str, Any]:
        """Test minimal required configuration."""
        # Set minimal required environment variables
        test_env = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test-key-minimal",
            "JWT_SECRET_KEY": "test-secret-key-minimal"
        }
        
        with self._temp_env(test_env):
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            # Verify defaults are applied
            assert config.llm.provider == LLMProvider.OPENAI
            assert config.llm.default_model == "gpt-3.5-turbo"
            assert config.cost.daily_limit == 100.0
            assert config.security.enable_pii_redaction is True
            assert len(config.security.presidio_entities) > 0
            
            return {
                "provider": config.llm.provider.value,
                "model": config.llm.default_model,
                "cost_limit": config.cost.daily_limit,
                "entities_count": len(config.security.presidio_entities)
            }
    
    def _test_full_config(self) -> Dict[str, Any]:
        """Test full configuration with all options."""
        test_env = {
            "ENVIRONMENT": "development",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test-key-full",
            "DEFAULT_MODEL": "gpt-4",
            "MAX_TOKENS": "2000",
            "TEMPERATURE": "0.5",
            "HELICONE_API_KEY": "sk-helicone-test",
            "COST_LIMIT_DAILY": "200.0",
            "CACHE_TTL_HOURS": "48",
            "PRESIDIO_ENTITIES": "PERSON,EMAIL_ADDRESS,PHONE_NUMBER,MEDICAL_LICENSE",
            "ENABLE_PII_REDACTION": "true",
            "ENABLE_GUARDRAILS": "true",
            "ENABLE_LLAMA_GUARD": "false",
            "ENABLE_NEMO_GUARDRAILS": "true",
            "GUARDRAILS_CONFIG_PATH": "config/custom_guardrails",
            "JWT_SECRET_KEY": "super-secret-full-config-key",
            "JWT_EXPIRE_MINUTES": "720",
            "PATIENT_MAX_QUERIES_PER_HOUR": "5",
            "PHYSICIAN_MAX_QUERIES_PER_HOUR": "50",
            "ADMIN_MAX_QUERIES_PER_HOUR": "500",
            "DATABASE_URL": "sqlite:///./test_full.db"
        }
        
        with self._temp_env(test_env):
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            # Verify custom values are applied
            assert config.environment == Environment.DEVELOPMENT
            assert config.debug is True
            assert config.log_level == LogLevel.DEBUG
            assert config.llm.default_model == "gpt-4"
            assert config.llm.max_tokens == 2000
            assert config.llm.temperature == 0.5
            assert config.cost.daily_limit == 200.0
            assert config.cost.cache_ttl_hours == 48
            assert len(config.security.presidio_entities) == 4
            assert config.security.enable_llama_guard is False
            assert config.rate_limit.patient_max_queries_per_hour == 5
            
            return {
                "environment": config.environment.value,
                "model": config.llm.default_model,
                "cost_limit": config.cost.daily_limit,
                "entities": config.security.presidio_entities,
                "rate_limits": {
                    "patient": config.rate_limit.patient_max_queries_per_hour,
                    "physician": config.rate_limit.physician_max_queries_per_hour,
                    "admin": config.rate_limit.admin_max_queries_per_hour
                }
            }
    
    def _test_production_config(self) -> Dict[str, Any]:
        """Test production-specific configuration requirements."""
        test_env = {
            "ENVIRONMENT": "production",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-prod-key",
            "JWT_SECRET_KEY": "production-secret-key-very-secure",
            "COST_LIMIT_DAILY": "500.0",
            "ENABLE_PII_REDACTION": "true",
            "ENABLE_GUARDRAILS": "true"
        }
        
        with self._temp_env(test_env):
            config_manager = ConfigManager()
            config = config_manager.load_config()
            
            # Verify production settings
            assert config.environment == Environment.PRODUCTION
            assert config.debug is False
            assert config.log_level == LogLevel.INFO
            assert config.auth.jwt_secret_key != "your-super-secret-jwt-key-change-this-in-production"
            
            return {
                "environment": config.environment.value,
                "debug": config.debug,
                "security_enabled": config.security.enable_pii_redaction and config.security.enable_guardrails
            }
    
    def _test_invalid_config(self) -> Dict[str, Any]:
        """Test handling of invalid configuration values."""
        test_env = {
            "LLM_PROVIDER": "invalid_provider",
            "OPENAI_API_KEY": "sk-test-key",
            "JWT_SECRET_KEY": "test-secret"
        }
        
        with self._temp_env(test_env):
            config_manager = ConfigManager()
            
            try:
                config_manager.load_config()
                raise AssertionError("Should have failed with invalid provider")
            except ConfigurationError as e:
                assert "Invalid LLM_PROVIDER" in str(e)
                return {"error_caught": True, "error_message": str(e)}
    
    def _test_missing_required(self) -> Dict[str, Any]:
        """Test handling of missing required variables."""
        # Clear all environment variables
        with self._temp_env({}):
            config_manager = ConfigManager()
            
            try:
                config_manager.load_config()
                raise AssertionError("Should have failed with missing required variables")
            except ConfigurationError as e:
                assert "Required environment variable" in str(e)
                return {"error_caught": True, "error_message": str(e)}
    
    def _test_guardrail_variations(self) -> Dict[str, Any]:
        """Test different guardrail configuration combinations."""
        variations = [
            {
                "name": "NeMo Only",
                "env": {
                    "ENABLE_NEMO_GUARDRAILS": "true",
                    "ENABLE_LLAMA_GUARD": "false",
                    "GUARDRAILS_CONFIG_PATH": "config/nemo_only"
                }
            },
            {
                "name": "Llama Guard Only", 
                "env": {
                    "ENABLE_NEMO_GUARDRAILS": "false",
                    "ENABLE_LLAMA_GUARD": "true"
                }
            },
            {
                "name": "Both Enabled",
                "env": {
                    "ENABLE_NEMO_GUARDRAILS": "true",
                    "ENABLE_LLAMA_GUARD": "true",
                    "GUARDRAILS_CONFIG_PATH": "config/both_enabled"
                }
            },
            {
                "name": "All Disabled",
                "env": {
                    "ENABLE_GUARDRAILS": "false",
                    "ENABLE_NEMO_GUARDRAILS": "false",
                    "ENABLE_LLAMA_GUARD": "false"
                }
            }
        ]
        
        results = []
        base_env = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test-key",
            "JWT_SECRET_KEY": "test-secret"
        }
        
        for variation in variations:
            test_env = {**base_env, **variation["env"]}
            
            with self._temp_env(test_env):
                config_manager = ConfigManager()
                config = config_manager.load_config()
                
                results.append({
                    "name": variation["name"],
                    "guardrails_enabled": config.security.enable_guardrails,
                    "nemo_enabled": config.security.enable_nemo_guardrails,
                    "llama_guard_enabled": config.security.enable_llama_guard,
                    "config_path": config.security.guardrails_config_path
                })
        
        return {"variations": results}
    
    def _test_cost_variations(self) -> Dict[str, Any]:
        """Test different cost limit and monitoring configurations."""
        variations = [
            {"daily_limit": "50.0", "alert_threshold": "90.0"},
            {"daily_limit": "100.0", "alert_threshold": "75.0"},
            {"daily_limit": "500.0", "alert_threshold": "80.0"},
            {"daily_limit": "1000.0", "alert_threshold": "95.0"}
        ]
        
        results = []
        base_env = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test-key",
            "JWT_SECRET_KEY": "test-secret"
        }
        
        for variation in variations:
            test_env = {
                **base_env,
                "COST_LIMIT_DAILY": variation["daily_limit"],
                "COST_ALERT_THRESHOLD": variation["alert_threshold"]
            }
            
            with self._temp_env(test_env):
                config_manager = ConfigManager()
                config = config_manager.load_config()
                
                results.append({
                    "daily_limit": config.cost.daily_limit,
                    "alert_threshold": config.cost.cost_alert_threshold,
                    "alert_amount": config.cost.daily_limit * (config.cost.cost_alert_threshold / 100)
                })
        
        return {"cost_variations": results}
    
    def _test_security_toggles(self) -> Dict[str, Any]:
        """Test different security feature toggle combinations."""
        toggles = [
            {
                "name": "All Security Enabled",
                "env": {
                    "ENABLE_PII_REDACTION": "true",
                    "ENABLE_GUARDRAILS": "true",
                    "ENABLE_MEDICAL_DISCLAIMERS": "true"
                }
            },
            {
                "name": "PII Only",
                "env": {
                    "ENABLE_PII_REDACTION": "true",
                    "ENABLE_GUARDRAILS": "false",
                    "ENABLE_MEDICAL_DISCLAIMERS": "false"
                }
            },
            {
                "name": "Guardrails Only",
                "env": {
                    "ENABLE_PII_REDACTION": "false",
                    "ENABLE_GUARDRAILS": "true",
                    "ENABLE_MEDICAL_DISCLAIMERS": "false"
                }
            },
            {
                "name": "Minimal Security",
                "env": {
                    "ENABLE_PII_REDACTION": "false",
                    "ENABLE_GUARDRAILS": "false",
                    "ENABLE_MEDICAL_DISCLAIMERS": "true"
                }
            }
        ]
        
        results = []
        base_env = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "sk-test-key",
            "JWT_SECRET_KEY": "test-secret"
        }
        
        for toggle in toggles:
            test_env = {**base_env, **toggle["env"]}
            
            with self._temp_env(test_env):
                config_manager = ConfigManager()
                config = config_manager.load_config()
                
                results.append({
                    "name": toggle["name"],
                    "pii_redaction": config.security.enable_pii_redaction,
                    "guardrails": config.security.enable_guardrails,
                    "medical_disclaimers": config.security.enable_medical_disclaimers,
                    "security_score": sum([
                        config.security.enable_pii_redaction,
                        config.security.enable_guardrails,
                        config.security.enable_medical_disclaimers
                    ])
                })
        
        return {"security_toggles": results}
    
    def _temp_env(self, env_vars: Dict[str, str]):
        """Context manager for temporary environment variables."""
        class TempEnv:
            def __init__(self, env_vars):
                self.env_vars = env_vars
                self.original_values = {}
            
            def __enter__(self):
                # Save original values and set new ones
                for key, value in self.env_vars.items():
                    self.original_values[key] = os.environ.get(key)
                    os.environ[key] = value
                
                # Clear other environment variables that might interfere
                keys_to_clear = [
                    "LLM_PROVIDER", "OPENAI_API_KEY", "JWT_SECRET_KEY",
                    "HELICONE_API_KEY", "COST_LIMIT_DAILY", "PRESIDIO_ENTITIES",
                    "ENABLE_PII_REDACTION", "ENABLE_GUARDRAILS", "ENABLE_LLAMA_GUARD",
                    "ENABLE_NEMO_GUARDRAILS", "GUARDRAILS_CONFIG_PATH",
                    "PATIENT_MAX_QUERIES_PER_HOUR", "PHYSICIAN_MAX_QUERIES_PER_HOUR",
                    "ADMIN_MAX_QUERIES_PER_HOUR", "ENVIRONMENT", "DEBUG", "LOG_LEVEL"
                ]
                
                for key in keys_to_clear:
                    if key not in self.env_vars and key in os.environ:
                        if key not in self.original_values:
                            self.original_values[key] = os.environ[key]
                        del os.environ[key]
                
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                # Restore original values
                for key, original_value in self.original_values.items():
                    if original_value is None:
                        if key in os.environ:
                            del os.environ[key]
                    else:
                        os.environ[key] = original_value
        
        return TempEnv(env_vars)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate test summary statistics."""
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed = len(self.test_results) - passed
        success_rate = (passed / len(self.test_results)) * 100 if self.test_results else 0
        
        return {
            "total": len(self.test_results),
            "passed": passed,
            "failed": failed,
            "success_rate": success_rate
        }


def main():
    """Run configuration validation tests."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    validator = ConfigValidator()
    results = validator.run_validation_tests()
    
    # Save results to file
    results_file = Path(__file__).parent.parent / "config_validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Return exit code based on results
    if results["summary"]["failed"] > 0:
        print("\n⚠️  Some configuration tests failed. Please review the results.")
        return 1
    else:
        print("\n🎉 All configuration tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())