"""
Test the actual API endpoint with frontend-like data
"""
import asyncio
import json
import aiohttp
from datetime import datetime


async def test_api_endpoint():
    """Test the actual PUT /rocks/{rock_id}/tasks API endpoint"""
    print("🧪 Testing API Endpoint with Frontend Data")
    print("=" * 60)
    
    # Test data that matches what frontend sends
    test_rock_id = "2c0251d6-ab96-4056-a2fa-66c151711cd0"  # Use existing rock from logs
    
    # Data structure that matches frontend logs
    test_task_data = [{
        "comments": [],
        "rock_id": test_rock_id,
        "sub_tasks": None,  # This was causing the 422 error
        "task": "Test task from API",
        "task_id": f"task_{int(datetime.now().timestamp() * 1000)}_test",
        "updated_at": datetime.now().isoformat() + "Z",
        "week": 1
    }]
    
    print(f"📝 Testing with task data: {json.dumps(test_task_data, indent=2)}")
    
    # Test the API endpoint
    url = f"http://localhost:8000/rocks/{test_rock_id}/tasks"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer your_token_here"  # Replace with actual token
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(url, json=test_task_data, headers=headers) as response:
                print(f"📊 Response Status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ API call successful!")
                    print(f"📋 Tasks created: {len(result.get('tasks', []))}")
                    for task in result.get('tasks', []):
                        print(f"   - {task.get('task')} (Week: {task.get('week')})")
                    return True
                else:
                    error_text = await response.text()
                    print(f"❌ API call failed: {response.status}")
                    print(f"📋 Error: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


async def main():
    print("🚀 Starting API endpoint test...")
    
    # Check if backend is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status == 404:  # Health endpoint might not exist
                    print("⚠️ Backend appears to be running (got 404 for /health)")
                else:
                    print("✅ Backend is running")
    except:
        print("❌ Backend not running. Please start with: python main.py")
        return
    
    success = await test_api_endpoint()
    
    if success:
        print("\n🎉 API test completed successfully!")
    else:
        print("\n❌ API test failed")


if __name__ == "__main__":
    asyncio.run(main())
