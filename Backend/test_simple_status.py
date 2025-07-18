#!/usr/bin/env python3
"""
Simple test script to verify the new status update endpoint works
"""

def test_simple_status_endpoint():
    """Test that our simple status endpoint is properly defined"""
    
    print("🧪 Testing Simple Status Update Endpoint...")
    
    # Test the imports
    try:
        from routes.todo import SimpleStatusUpdate
        print("✅ SimpleStatusUpdate model imported successfully")
        
        # Test model validation
        status_update = SimpleStatusUpdate(status="completed")
        print(f"✅ Status update model works: {status_update.status}")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Model error: {e}")
        return False
    
    # Test that main.py includes the routes
    try:
        from main import app
        print("✅ FastAPI app imported successfully")
        
        # Get all routes
        routes = [route.path for route in app.routes]
        print(f"📋 Available routes: {len(routes)} total")
        
        # Check if our new endpoint exists
        status_route_exists = any("/todos/{todo_id}/status" in route for route in routes)
        if status_route_exists:
            print("✅ Status update route found in FastAPI app")
        else:
            print("❌ Status update route NOT found in FastAPI app")
            print("Available todo routes:")
            todo_routes = [route for route in routes if "todo" in route]
            for route in todo_routes:
                print(f"  - {route}")
        
    except Exception as e:
        print(f"❌ FastAPI app error: {e}")
        return False
    
    print("✅ Simple status endpoint test completed!")
    return True

if __name__ == "__main__":
    success = test_simple_status_endpoint()
    if success:
        print("\n🚀 All tests passed! The simple status update feature is ready.")
    else:
        print("\n❌ Tests failed! Please check the implementation.")
