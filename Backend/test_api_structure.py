"""
Quick validation script for VTO API endpoints
Tests that all routes are properly registered and accessible
"""

import requests
import asyncio
from fastapi.testclient import TestClient
from main import app

def test_api_endpoints():
    """Test that all API endpoints are accessible"""
    client = TestClient(app)
    
    print("Testing VTO API Endpoints...")
    print("="*50)
    
    # Test root endpoint
    try:
        response = client.get("/")
        print(f"✅ Root endpoint: {response.status_code}")
        if response.status_code == 200:
            print(f"   API Version: {response.json().get('version')}")
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")
    
    # Test docs endpoint
    try:
        response = client.get("/docs")
        print(f"✅ Docs endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Docs endpoint failed: {e}")
    
    # Test new VTO endpoints (without authentication for now)
    endpoints_to_test = [
        "/api/meetings",
        "/api/todos", 
        "/api/milestones",
        "/api/time-slots",
        "/api/analytics/dashboard/overview",
        "/api/rag/search",
        "/api/sessions/day-sessions/test-id"
    ]
    
    print("\nTesting VTO Endpoints (structure only):")
    print("-" * 40)
    
    for endpoint in endpoints_to_test:
        try:
            # We expect 401/422 for protected endpoints, but not 404
            response = client.get(endpoint)
            if response.status_code in [401, 422, 403]:
                print(f"✅ {endpoint}: Registered (auth required)")
            elif response.status_code == 404:
                print(f"❌ {endpoint}: Not found")
            else:
                print(f"✅ {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Error - {e}")
    
    print("\n" + "="*50)
    print("API Structure Validation Complete")
    print("="*50)

if __name__ == "__main__":
    test_api_endpoints()
