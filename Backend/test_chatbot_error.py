"""
Test script to identify the 500 error in chatbot quick-action endpoint
"""

import asyncio
import sys
import os
from uuid import UUID

# Add the Backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from service.chatbot_service import chatbot_service

async def test_quick_action():
    """Test the quick action functionality that's causing 500 errors"""
    
    # Test context data retrieval for a rock (use the ID from the logs)
    test_rock_id = UUID("c6597f43-8d92-4e14-b190-79b4feb8c3bf")
    
    try:
        print("Testing rock context data retrieval...")
        context_data = await chatbot_service.get_context_data("rock", test_rock_id)
        print(f"Context data result: {context_data}")
        
        if context_data:
            print("\nTesting chat with rock context...")
            result = await chatbot_service.chat(
                user_question="Explain this rock's objective",
                context_type="rock",
                context_id=test_rock_id
            )
            print(f"Chat result: {result}")
        else:
            print("No context data found for the rock")
            
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_quick_action())
