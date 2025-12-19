#!/usr/bin/env python3

import traceback

print("Attempting to execute guardrails.py...")

try:
    with open('src/security/guardrails.py', 'r') as f:
        code = f.read()
    
    print(f"File read successfully, {len(code)} characters")
    
    # Try to compile first
    compiled = compile(code, 'src/security/guardrails.py', 'exec')
    print("Code compiled successfully")
    
    # Now execute
    globals_dict = {}
    exec(compiled, globals_dict)
    
    print("Code executed successfully")
    print("Defined names:", [name for name in globals_dict.keys() if not name.startswith('__')])
    
    # Check for specific classes
    if 'GuardrailsService' in globals_dict:
        print("✓ GuardrailsService found")
    else:
        print("✗ GuardrailsService not found")
        
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()