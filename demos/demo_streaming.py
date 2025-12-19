#!/usr/bin/env python3
"""
Streaming Response Demo
Demonstrates real-time streaming responses from the Secure Medical Chat API
"""

import requests
import json
import time

def demo_streaming():
    """Demonstrate streaming chat response"""
    print("🌊 STREAMING RESPONSE DEMO")
    print("=" * 50)
    
    # Prepare request
    url = "http://localhost:8000/api/chat/stream"
    data = {
        "message": "Explain the cardiovascular system in simple terms",
        "user_role": "patient"
    }
    
    print(f"📤 Sending request: {data['message']}")
    print("📥 Streaming response:")
    print("-" * 30)
    
    try:
        # Make streaming request
        response = requests.post(
            url,
            json=data,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        try:
                            data_str = line_str[6:]  # Remove 'data: ' prefix
                            if data_str.strip() == '[DONE]':
                                break
                            
                            chunk_data = json.loads(data_str)
                            
                            if chunk_data.get('type') == 'token':
                                print(chunk_data.get('content', ''), end='', flush=True)
                            elif chunk_data.get('type') == 'metadata':
                                print(f"\n\n📊 Final metadata:")
                                print(f"   Cost: ${chunk_data.get('cost', 0)}")
                                print(f"   Latency: {chunk_data.get('latency_ms', 0)}ms")
                                print(f"   Model: {chunk_data.get('model_used', 'unknown')}")
                                
                        except json.JSONDecodeError:
                            continue
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Streaming error: {e}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    demo_streaming()