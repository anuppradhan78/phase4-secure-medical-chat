#!/usr/bin/env python3
"""
Security Check Script

This script helps ensure that no real API keys or secrets are accidentally
committed to version control and that the environment is properly configured.
"""

import os
import re
import sys
from pathlib import Path


def check_for_real_api_keys():
    """Check for potentially real API keys in the codebase."""
    print("🔍 Checking for Real API Keys...")
    print("=" * 50)
    
    # Patterns that indicate real API keys (not demo/test keys)
    suspicious_patterns = [
        r'sk-[a-zA-Z0-9]{48,}',  # Real OpenAI keys are longer
        r'sk-helicone-[a-zA-Z0-9]{32,}',  # Real Helicone keys
        r'sk-proj-[a-zA-Z0-9]+',  # OpenAI project keys
    ]
    
    # Known safe demo/test patterns
    safe_patterns = [
        'sk-test-',
        'sk-demo-',
        'sk-your-',
        'sk-helicone-your-',
        'sk-fake-',
        'sk-dev-key-replace',
        'sk-prod-key-from-secrets',
        'sk-secure-facility-key',
        'sk-cost-optimized-key',
        'sk-research-key',
        'sk-prod-key',
        'sk-helicone-test',
        'sk-helicone-prod-key',
        'sk-helicone-cost-tracking',
        'sk-helicone-xxxxxxxx',  # Documentation placeholder
        'xxxxxxxx'  # Any key with x's is a placeholder
    ]
    
    issues_found = []
    files_to_check = []
    
    # Get all Python and config files
    for file_path in Path('.').rglob('*'):
        if file_path.is_file() and file_path.suffix in ['.py', '.md', '.env', '.example', '.txt']:
            if 'venv' not in str(file_path) and '.git' not in str(file_path):
                files_to_check.append(file_path)
    
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                for pattern in suspicious_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # Check if it's a known safe pattern
                        is_safe = any(safe_pattern in match for safe_pattern in safe_patterns)
                        
                        # Also check for placeholder patterns (repeated characters)
                        if 'xxxx' in match or 'yyyy' in match or 'zzzz' in match:
                            is_safe = True
                        
                        # Check for documentation context
                        if any(word in str(file_path).lower() for word in ['readme', 'setup', 'doc', 'example']):
                            if 'xxxx' in match or len(set(match[-10:])) <= 2:  # Repeated chars at end
                                is_safe = True
                        
                        if not is_safe:
                            issues_found.append({
                                'file': str(file_path),
                                'key': match,
                                'type': 'Potentially Real API Key'
                            })
        except (UnicodeDecodeError, PermissionError):
            continue
    
    if issues_found:
        print("❌ POTENTIAL SECURITY ISSUES FOUND:")
        for issue in issues_found:
            print(f"   File: {issue['file']}")
            print(f"   Issue: {issue['type']}")
            print(f"   Key: {issue['key'][:20]}...")
            print()
        return False
    else:
        print("✅ No real API keys found in codebase")
        print("   All keys appear to be demo/test placeholders")
        return True


def check_gitignore():
    """Check that .gitignore properly excludes sensitive files."""
    print("\n🔒 Checking .gitignore Configuration...")
    print("=" * 50)
    
    gitignore_path = Path('.gitignore')
    if not gitignore_path.exists():
        print("❌ No .gitignore file found!")
        return False
    
    with open(gitignore_path, 'r') as f:
        gitignore_content = f.read()
    
    required_patterns = [
        '.env',
        '*.log',
        '__pycache__/',
        '*.db',
        'venv/',
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if pattern not in gitignore_content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print("⚠️  Missing .gitignore patterns:")
        for pattern in missing_patterns:
            print(f"   - {pattern}")
        return False
    else:
        print("✅ .gitignore properly configured")
        print("   All sensitive file patterns are excluded")
        return True


def check_env_files():
    """Check for .env files that shouldn't be committed."""
    print("\n📁 Checking Environment Files...")
    print("=" * 50)
    
    env_files = list(Path('.').glob('.env*'))
    
    # Remove .env.example as it's allowed
    allowed_files = ['.env.example']
    problematic_files = [f for f in env_files if f.name not in allowed_files]
    
    if problematic_files:
        print("⚠️  Found .env files that might contain secrets:")
        for file_path in problematic_files:
            print(f"   - {file_path}")
            # Check if it contains real-looking keys
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                    if re.search(r'sk-[a-zA-Z0-9]{20,}', content):
                        print(f"     ⚠️  Contains API key patterns")
            except:
                pass
        print("\n💡 Recommendation:")
        print("   - Ensure these files are in .gitignore")
        print("   - Remove any real API keys from these files")
        print("   - Use .env.example for documentation only")
        return False
    else:
        print("✅ No problematic .env files found")
        print("   Only .env.example exists (which is correct)")
        return True


def check_configuration_security():
    """Check configuration security best practices."""
    print("\n⚙️  Checking Configuration Security...")
    print("=" * 50)
    
    recommendations = []
    
    # Check if .env.example has proper placeholders
    env_example_path = Path('.env.example')
    if env_example_path.exists():
        with open(env_example_path, 'r') as f:
            content = f.read()
            
        if 'sk-your-' in content:
            print("✅ .env.example uses proper placeholders")
        else:
            recommendations.append("Use clear placeholders in .env.example")
    
    # Check for hardcoded secrets in Python files
    python_files = list(Path('.').rglob('*.py'))
    hardcoded_secrets = []
    
    for py_file in python_files:
        if 'venv' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Look for hardcoded API keys (not in comments or strings that are clearly examples)
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if ('api_key' in line.lower() or 'secret' in line.lower()) and '=' in line:
                    if not line.strip().startswith('#') and 'sk-' in line:
                        # Check if it's in a test/demo context
                        if not any(word in line.lower() for word in ['test', 'demo', 'example', 'fake']):
                            hardcoded_secrets.append(f"{py_file}:{i+1}")
        except:
            continue
    
    if hardcoded_secrets:
        print("⚠️  Potential hardcoded secrets found:")
        for secret in hardcoded_secrets:
            print(f"   - {secret}")
        recommendations.append("Move hardcoded secrets to environment variables")
    else:
        print("✅ No hardcoded secrets found in Python files")
    
    if recommendations:
        print("\n💡 Security Recommendations:")
        for rec in recommendations:
            print(f"   - {rec}")
        return False
    
    return True


def main():
    """Run all security checks."""
    print("🛡️  Security Check for Secure Medical Chat")
    print("=" * 60)
    print("Checking for potential security issues in the codebase...\n")
    
    checks = [
        ("API Key Check", check_for_real_api_keys),
        ("Gitignore Check", check_gitignore),
        ("Environment Files Check", check_env_files),
        ("Configuration Security Check", check_configuration_security),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Error in {check_name}: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("📊 SECURITY CHECK SUMMARY")
    print("=" * 60)
    print(f"Total Checks: {len(checks)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL SECURITY CHECKS PASSED!")
        print("✅ No security issues found in the codebase")
        print("\n💡 Best Practices:")
        print("   - Keep your .env file out of version control")
        print("   - Use strong, unique API keys for production")
        print("   - Regularly rotate your API keys")
        print("   - Monitor API usage for unusual activity")
    else:
        print(f"\n⚠️  {failed} security issues found")
        print("Please review and fix the issues above before deploying")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)