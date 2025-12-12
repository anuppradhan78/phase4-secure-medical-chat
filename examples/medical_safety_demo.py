#!/usr/bin/env python3
"""
Demo script for medical safety controls.
Tests automatic disclaimers, emergency detection, and medical knowledge grounding.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.security.medical_safety import create_medical_safety_controller


def test_medical_safety_controls():
    """Test the medical safety controls with various scenarios."""
    print("🏥 Medical Safety Controls Demo")
    print("=" * 50)
    
    # Create medical safety controller
    controller = create_medical_safety_controller()
    
    # Test cases for different scenarios
    test_cases = [
        {
            "name": "Emergency Situation - Chest Pain",
            "message": "I have severe chest pain and shortness of breath",
            "response": "Based on your symptoms, this could be related to several conditions."
        },
        {
            "name": "Medication Dosage Request (Should be blocked)",
            "message": "How much ibuprofen should I take for my headache?",
            "response": "For pain relief, you might consider over-the-counter options."
        },
        {
            "name": "General Medical Question",
            "message": "I have a headache that won't go away",
            "response": "Headaches can be caused by various factors including stress, dehydration, or tension."
        },
        {
            "name": "Non-medical Question",
            "message": "What's the weather like today?",
            "response": "I don't have access to current weather information."
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)
        print(f"User Message: {test_case['message']}")
        
        # Validate input
        validation_result = controller.validate_input(test_case['message'])
        print(f"Input Validation: {'BLOCKED' if validation_result.blocked else 'ALLOWED'}")
        
        if validation_result.blocked:
            print(f"Block Reason: {validation_result.reason}")
            print(f"Risk Score: {validation_result.risk_score}")
        else:
            # Enhance response with safety controls
            enhanced_response = controller.enhance_response(
                test_case['response'], 
                test_case['message']
            )
            print(f"Original Response: {test_case['response']}")
            print(f"Enhanced Response: {enhanced_response}")
        
        if validation_result.guardrail_flags:
            print(f"Guardrail Flags: {validation_result.guardrail_flags}")
    
    # Display safety statistics
    print(f"\n📊 Safety Statistics")
    print("-" * 40)
    stats = controller.get_safety_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    try:
        test_medical_safety_controls()
        print(f"\n✅ Medical Safety Controls Demo completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()