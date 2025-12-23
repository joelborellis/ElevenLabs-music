"""
Debug script to check environment variable loading.
"""

import os
from dotenv import load_dotenv

print("=" * 80)
print("Environment Variable Debug Script")
print("=" * 80)

print("\n1. Before load_dotenv():")
print(f"   OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")

print("\n2. Loading .env file...")
load_dotenv()

print("\n3. After load_dotenv():")
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    print(f"   OPENAI_API_KEY: SET (length: {len(api_key)} chars)")
    print(f"   First 10 chars: {api_key[:10]}...")
    print(f"   Last 10 chars: ...{api_key[-10:]}")
else:
    print("   OPENAI_API_KEY: NOT SET")

print("\n4. Attempting to import OpenAI Agent...")
try:
    from agents import Agent
    print("   ✓ Agent imported successfully")
    
    print("\n5. Attempting to create Agent...")
    try:
        agent = Agent(
            name="test_agent",
            instructions="You are a test agent",
            output_type=str
        )
        print(f"   ✓ Agent created successfully: {agent.name}")
    except Exception as e:
        print(f"   ✗ Agent creation failed: {e}")
        
except Exception as e:
    print(f"   ✗ Agent import failed: {e}")

print("\n" + "=" * 80)
