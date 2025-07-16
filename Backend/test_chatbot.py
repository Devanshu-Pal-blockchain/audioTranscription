"""
Test script for Chatbot API endpoints
Run this to test the chatbot functionality
"""

import asyncio
import uuid
from service.chatbot_service import chatbot_service

async def test_chatbot_service():
    """Test the chatbot service directly"""
    print("🤖 Testing Chatbot Service")
    print("=" * 50)
    
    # Test 1: General EOS question
    print("\n1. Testing General EOS Question:")
    print("-" * 30)
    
    general_response = await chatbot_service.chat(
        user_question="What is EOS and how do rocks work?",
        context_type=None,
        context_id=None
    )
    
    print(f"Mode: {general_response['mode']}")
    print(f"Response: {general_response['response'][:200]}...")
    print(f"Options: {general_response['predefined_options'][:3]}...")
    
    # Test 2: Predefined options
    print("\n2. Testing Predefined Options:")
    print("-" * 30)
    
    rock_options = chatbot_service.get_predefined_options("rock")
    issue_options = chatbot_service.get_predefined_options("issue")
    todo_options = chatbot_service.get_predefined_options("todo")
    general_options = chatbot_service.get_predefined_options(None)
    
    print(f"Rock options: {rock_options}")
    print(f"Issue options: {issue_options}")
    print(f"Todo options: {todo_options}")
    print(f"General options: {general_options}")
    
    # Test 3: Context data retrieval (will fail without actual data, but tests the structure)
    print("\n3. Testing Context Data Retrieval:")
    print("-" * 30)
    
    fake_uuid = uuid.uuid4()
    rock_context = await chatbot_service.get_context_data("rock", fake_uuid)
    print(f"Rock context (should be None): {rock_context}")
    
    print("\n✅ All tests completed!")
    
    return True

if __name__ == "__main__":
    try:
        asyncio.run(test_chatbot_service())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
