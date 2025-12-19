"""
Simple test of guardrails functionality.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    # Try to import the module
    import security.guardrails as guardrails_module
    print("Module imported successfully")
    print("Available attributes:", [attr for attr in dir(guardrails_module) if not attr.startswith('_')])
    
    # Try to get the class
    if hasattr(guardrails_module, 'GuardrailsService'):
        GuardrailsService = guardrails_module.GuardrailsService
        print("GuardrailsService found!")
        
        # Test instantiation
        service = GuardrailsService()
        print("Service created successfully")
        
        # Test basic functionality
        result = service.validate_input("test message")
        print(f"Test validation result: {result}")
        
    else:
        print("GuardrailsService not found in module")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()