#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""

print("Testing imports...")

try:
    from src.memory_agent import MemoryAgent, MemoryType, Memory
    print("✅ Memory agent imports successful")
except Exception as e:
    print(f"❌ Memory agent import error: {e}")

try:
    from src.storage.memory_storage import MemoryStorage
    print("✅ Storage imports successful")
except Exception as e:
    print(f"❌ Storage import error: {e}")

try:
    from src.clients import InternalMCPClient
    print("✅ Client imports successful")
except Exception as e:
    print(f"❌ Client import error: {e}")

try:
    from tools.tool_memory_orchestrator_sse import process_user_prompt
    print("✅ Tool imports successful")
except Exception as e:
    print(f"❌ Tool import error: {e}")

print("\nTesting basic functionality...")

try:
    # Create memory agent
    agent = MemoryAgent()
    print("✅ Memory agent created")
    
    # Create a test memory
    memory = Memory(
        user_id="test_user",
        session_id="test_session",
        type=MemoryType.FACT,
        content="Test memory content"
    )
    print("✅ Memory object created")
    
    # Test intelligence
    should_store = agent.intelligence.should_store("I am a Python developer")
    print(f"✅ Intelligence check: should_store = {should_store}")
    
except Exception as e:
    print(f"❌ Functionality test error: {e}")

print("\nAll tests completed!")