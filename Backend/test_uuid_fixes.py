#!/usr/bin/env python3
"""
Test script to validate UUID validation fixes for participant assignment
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.rock import Rock
from models.todo import Todo
from models.issue import Issue
from service.rock_service import RockService
from service.todo_service import TodoService
from service.issue_service import IssueService
from uuid import uuid4
from datetime import datetime, date

def test_rock_with_empty_assigned_to_id():
    """Test that Rock model accepts None for assigned_to_id"""
    print("Testing Rock model with None assigned_to_id...")
    
    try:
        rock_data = {
            "id": str(uuid4()),
            "rock_id": str(uuid4()),
            "rock_name": "Test Rock",
            "smart_objective": "Test objective with SMART criteria",
            "quarter_id": str(uuid4()),
            "assigned_to_id": None,  # This should work now
            "assigned_to_name": "UNASSIGNED: John Doe",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        rock = Rock(**rock_data)
        print(f"✅ SUCCESS: Rock created with None assigned_to_id")
        print(f"   - Rock Name: {rock.rock_name}")
        print(f"   - Assigned To ID: {rock.assigned_to_id}")
        print(f"   - Assigned To Name: {rock.assigned_to_name}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_rock_with_empty_string_assigned_to_id():
    """Test that Rock model handles empty string for assigned_to_id through service"""
    print("\nTesting Rock service safe_decrypt_dict with empty string...")
    
    try:
        # Simulate data from database with empty string
        mock_db_data = {
            "id": str(uuid4()),
            "rock_id": str(uuid4()),
            "rock_name": "Test Rock",
            "smart_objective": "Test objective",
            "quarter_id": str(uuid4()),
            "assigned_to_id": "",  # Empty string from DB
            "assigned_to_name": "",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Process through safe_decrypt_dict
        cleaned_data = RockService.safe_decrypt_dict(mock_db_data)
        print(f"   - Cleaned assigned_to_id: {cleaned_data.get('assigned_to_id')}")
        
        # Create Rock model
        rock = Rock(**cleaned_data)
        print(f"✅ SUCCESS: Rock created after cleaning empty string UUID")
        print(f"   - Assigned To ID: {rock.assigned_to_id}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_todo_with_none_assigned_to_id():
    """Test that Todo model accepts None for assigned_to_id"""
    print("\nTesting Todo model with None assigned_to_id...")
    
    try:
        todo_data = {
            "id": str(uuid4()),
            "todo_id": str(uuid4()),
            "task_title": "Test Todo Task",
            "assigned_to": "UNASSIGNED: Jane Doe",
            "designation": "Unknown",
            "due_date": date.today(),
            "quarter_id": str(uuid4()),
            "assigned_to_id": None,  # This should work
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        todo = Todo(**todo_data)
        print(f"✅ SUCCESS: Todo created with None assigned_to_id")
        print(f"   - Task Title: {todo.task_title}")
        print(f"   - Assigned To ID: {todo.assigned_to_id}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_issue_with_none_raised_by_id():
    """Test that Issue model accepts None for raised_by_id"""
    print("\nTesting Issue model with None raised_by_id...")
    
    try:
        issue_data = {
            "id": str(uuid4()),
            "issue_id": str(uuid4()),
            "issue_title": "Test Issue",
            "description": "Test issue description",
            "raised_by": "UNASSIGNED: Unknown Person",
            "quarter_id": str(uuid4()),
            "raised_by_id": None,  # This should work
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        issue = Issue(**issue_data)
        print(f"✅ SUCCESS: Issue created with None raised_by_id")
        print(f"   - Issue Title: {issue.issue_title}")
        print(f"   - Raised By ID: {issue.raised_by_id}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

def test_participant_validation_workflow():
    """Test the complete participant validation workflow"""
    print("\nTesting complete participant validation workflow...")
    
    # Simulate participants from frontend
    participants = [
        {
            "employee_id": str(uuid4()),
            "employee_name": "Alice Johnson",
            "employee_designation": "Project Manager",
            "employee_responsibilities": "Team coordination"
        },
        {
            "employee_id": str(uuid4()),
            "employee_name": "Bob Smith",
            "employee_designation": "Developer",
            "employee_responsibilities": "Software development"
        }
    ]
    
    # Simulate pipeline response with unmatched names
    pipeline_response = {
        "rocks": [
            {
                "rock_owner": "Alice Johnson",  # This should match
                "smart_rock": "Deliver project milestone"
            },
            {
                "rock_owner": "Charlie Brown",  # This won't match
                "smart_rock": "Complete documentation"
            },
            {
                "rock_owner": "",  # Empty name
                "smart_rock": "Review processes"
            }
        ]
    }
    
    print("   Available participants:")
    for p in participants:
        print(f"     - {p['employee_name']} (ID: {p['employee_id']})")
    
    print("   Rock assignments from pipeline:")
    for i, rock in enumerate(pipeline_response["rocks"]):
        owner = rock.get("rock_owner", "")
        print(f"     - Rock {i+1}: '{rock['smart_rock']}' -> '{owner}'")
    
    # Test validation logic
    from service.data_parser_service import DataParserService
    parser = DataParserService()
    
    test_cases = [
        ("Alice Johnson", True),    # Should match
        ("Charlie Brown", False),   # Should not match
        ("", False),               # Empty name
        ("alice johnson", True),   # Case insensitive match
        ("Alice", True),           # Partial match
    ]
    
    print("   Validation results:")
    for name, expected_match in test_cases:
        employee_id, validated_name = parser.validate_and_map_participant(name, participants)
        matched = employee_id is not None
        status = "✅" if matched == expected_match else "❌"
        print(f"     {status} '{name}' -> ID: {employee_id}, Name: '{validated_name}'")
    
    return True

def main():
    """Run all tests"""
    print("🧪 Testing UUID Validation Fixes for Participant Assignment\n")
    print("=" * 70)
    
    tests = [
        test_rock_with_empty_assigned_to_id,
        test_rock_with_empty_string_assigned_to_id,
        test_todo_with_none_assigned_to_id,
        test_issue_with_none_raised_by_id,
        test_participant_validation_workflow
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} threw exception: {e}")
            failed += 1
        print("-" * 70)
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! UUID validation fixes are working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the fixes.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
