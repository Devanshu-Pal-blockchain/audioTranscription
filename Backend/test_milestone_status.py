#!/usr/bin/env python3

import asyncio
import aiohttp
import json

async def test_milestone_status_update():
    """Test milestone status update endpoint"""
    
    # Test configuration
    BASE_URL = "http://localhost:8000"
    
    # Mock data - you should replace these with actual IDs from your database
    test_task_id = "123e4567-e89b-12d3-a456-426614174000"  # Replace with actual task ID
    
    async with aiohttp.ClientSession() as session:
        
        print("🧪 Testing milestone status update endpoint...")
        
        # Test the PUT /tasks/{task_id}/status endpoint
        status_update_url = f"{BASE_URL}/tasks/{test_task_id}/status"
        status_data = {"status": "completed"}
        
        try:
            async with session.put(
                status_update_url,
                json=status_data,
                headers={'Content-Type': 'application/json'}
            ) as response:
                
                print(f"📡 PUT {status_update_url}")
                print(f"📤 Request data: {status_data}")
                print(f"📥 Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Success: {json.dumps(result, indent=2)}")
                elif response.status == 404:
                    print(f"❌ Task not found (expected if using dummy ID)")
                elif response.status == 403:
                    print(f"❌ Forbidden - check authentication/permissions")
                else:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    
        except Exception as e:
            print(f"❌ Connection error: {e}")
            print("🔧 Make sure backend server is running on port 8000")

if __name__ == "__main__":
    print("🚀 Starting milestone status update test...")
    asyncio.run(test_milestone_status_update())
    print("✅ Test completed!")
