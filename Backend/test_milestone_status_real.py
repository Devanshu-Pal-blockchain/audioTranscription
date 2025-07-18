import requests
import json

# Test milestone status update endpoint with real data
BASE_URL = "http://localhost:8000"

def test_milestone_status_update():
    """Test updating milestone status with real data"""
    
    print("🧪 Testing milestone status update endpoint...")
    
    # First, let's get a list of quarters to find real milestone IDs
    print("\n1. Getting quarters to find real milestone data...")
    try:
        quarters_response = requests.get(f"{BASE_URL}/quarters/status/1")
        
        if quarters_response.status_code != 200:
            print(f"❌ Failed to get quarters: {quarters_response.status_code}")
            print(f"💡 Response: {quarters_response.text}")
            return
        
        quarters = quarters_response.json()
        print(f"✅ Found {len(quarters)} quarters")
        
        # Get a specific quarter with milestones
        if not quarters:
            print("❌ No quarters found")
            return
            
        first_quarter_id = quarters[0]['id']
        print(f"📊 Testing with quarter: {first_quarter_id}")
        
        # Get quarter details with milestones
        quarter_response = requests.get(f"{BASE_URL}/quarters/{first_quarter_id}/all")
        
        if quarter_response.status_code != 200:
            print(f"❌ Failed to get quarter details: {quarter_response.status_code}")
            print(f"💡 Response: {quarter_response.text}")
            return
        
        quarter_data = quarter_response.json()
        
        # Find a milestone to test with
        milestone_id = None
        current_status = None
        
        if 'rocks' in quarter_data and quarter_data['rocks']:
            for rock in quarter_data['rocks']:
                if 'milestones' in rock and rock['milestones']:
                    # Look for milestones in weekly format
                    for week_key, week_data in rock['milestones'].items():
                        if isinstance(week_data, dict) and ('milestones' in week_data or 'tasks' in week_data):
                            milestones = week_data.get('milestones') or week_data.get('tasks', [])
                            if milestones and isinstance(milestones, list):
                                first_milestone = milestones[0]
                                milestone_id = first_milestone.get('id') or first_milestone.get('task_id')
                                current_status = first_milestone.get('status', 'pending')
                                print(f"🎯 Found milestone to test: {milestone_id} (current status: {current_status})")
                                break
                    if milestone_id:
                        break
        
        if not milestone_id:
            print("❌ No milestones found to test with")
            print("💡 Quarter data structure:")
            print(json.dumps(quarter_data, indent=2, default=str)[:500] + "...")
            return
        
        print(f"\n2. Testing milestone status update for ID: {milestone_id}")
        
        # Test updating milestone status (toggle the current status)
        new_status = "completed" if current_status != "completed" else "pending"
        update_data = {
            "status": new_status
        }
        
        update_response = requests.put(
            f"{BASE_URL}/tasks/{milestone_id}/status",
            json=update_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📤 PUT /tasks/{milestone_id}/status")
        print(f"📦 Request data: {json.dumps(update_data, indent=2)}")
        print(f"📨 Response status: {update_response.status_code}")
        
        if update_response.status_code == 200:
            response_data = update_response.json()
            print(f"✅ Milestone status updated successfully!")
            print(f"📋 Response: {json.dumps(response_data, indent=2, default=str)}")
        else:
            print(f"❌ Failed to update milestone status")
            print(f"💡 Response: {update_response.text}")
        
        # Test toggling back to original status
        print(f"\n3. Testing toggle back to original status ({current_status})...")
        
        toggle_data = {
            "status": current_status
        }
        
        toggle_response = requests.put(
            f"{BASE_URL}/tasks/{milestone_id}/status",
            json=toggle_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"📤 PUT /tasks/{milestone_id}/status")
        print(f"📦 Request data: {json.dumps(toggle_data, indent=2)}")
        print(f"📨 Response status: {toggle_response.status_code}")
        
        if toggle_response.status_code == 200:
            response_data = toggle_response.json()
            print(f"✅ Milestone status toggled back successfully!")
            print(f"📋 Response: {json.dumps(response_data, indent=2, default=str)}")
        else:
            print(f"❌ Failed to toggle milestone status")
            print(f"💡 Response: {toggle_response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Could not connect to backend server")
        print("💡 Make sure the backend server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_milestone_status_update()
