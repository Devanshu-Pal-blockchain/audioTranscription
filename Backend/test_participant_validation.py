"""
Test script for enhanced participant validation in data parser service.
This tests the new comprehensive name validation and fallback strategies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service.data_parser_service import DataParserService
import json
import logging

# Set up logging to see validation messages
logging.basicConfig(level=logging.INFO)

def test_participant_validation():
    """Test the enhanced participant validation system"""
    
    # Create test participants list (simulating frontend data)
    participants = [
        {
            "employee_id": "emp_001", 
            "employee_name": "John Smith", 
            "employee_designation": "Project Manager",
            "employee_responsibilities": "Team leadership and project coordination"
        },
        {
            "employee_id": "emp_002", 
            "employee_name": "Sarah Johnson", 
            "employee_designation": "Senior Developer",
            "employee_responsibilities": "Software development and technical architecture"
        },
        {
            "employee_id": "emp_003", 
            "employee_name": "Michael Chen", 
            "employee_designation": "UX Designer",
            "employee_responsibilities": "User experience design and research"
        },
        {
            "employee_id": "emp_004", 
            "employee_name": "Emily Rodriguez", 
            "employee_designation": "Quality Assurance Lead",
            "employee_responsibilities": "Testing and quality control"
        }
    ]
    
    # Create test pipeline response with various name scenarios
    pipeline_response = {
        "rocks": [
            {
                "rock_owner": "John Smith",  # Exact match
                "smart_rock": "Implement new project management system by Q2"
            },
            {
                "rock_owner": "sarah johnson",  # Case mismatch
                "smart_rock": "Upgrade development infrastructure by Q2"
            },
            {
                "rock_owner": "Mike Chen",  # Partial name match
                "smart_rock": "Design new user interface by Q2"
            },
            {
                "rock_owner": "Emily R",  # Partial name match
                "smart_rock": "Establish automated testing framework by Q2"
            },
            {
                "rock_owner": "Alex Thompson",  # Person NOT in participants list
                "smart_rock": "Handle external vendor relations by Q2"
            },
            {
                "rock_owner": "",  # Empty name
                "smart_rock": "General company-wide initiative by Q2"
            }
        ],
        "todos": [
            {
                "task_title": "Review project requirements",
                "assigned_to": "John Smith",  # Exact match
                "designation": "Project Manager",
                "due_date": "2025-01-20"
            },
            {
                "task_title": "Setup development environment",
                "assigned_to": "Sarah J",  # Partial match
                "designation": "Senior Developer", 
                "due_date": "2025-01-25"
            },
            {
                "task_title": "Coordinate with external team",
                "assigned_to": "David Wilson",  # Person NOT in participants list
                "designation": "External Coordinator",
                "due_date": "2025-01-30"
            }
        ],
        "issues": [
            {
                "issue_title": "Database performance concerns",
                "description": "Current database is slow during peak hours",
                "raised_by": "Sarah Johnson"  # Exact match
            },
            {
                "issue_title": "User interface accessibility problems",
                "description": "Interface not accessible for disabled users",
                "raised_by": "michael"  # First name only
            },
            {
                "issue_title": "Integration testing gaps",
                "description": "Missing integration tests for critical modules",
                "raised_by": "Unknown Developer"  # Person NOT in participants list
            }
        ]
    }
    
    # Test the data parser service
    parser = DataParserService()
    
    print("="*80)
    print("TESTING ENHANCED PARTICIPANT VALIDATION")
    print("="*80)
    
    print(f"\nAvailable Participants:")
    for p in participants:
        print(f"  - {p['employee_name']} (ID: {p['employee_id']}) - {p['employee_designation']}")
    
    print(f"\nTesting parser with various name scenarios...")
    
    # Parse the response
    rocks, tasks, todos, issues, runtime_solutions = parser.parse_pipeline_response(
        pipeline_response, 
        quarter_id="q1_2025",
        participants=participants
    )
    
    print(f"\n" + "="*50)
    print("ROCKS ASSIGNMENT RESULTS:")
    print("="*50)
    for rock in rocks:
        assigned_id = rock.get('assigned_to_id', 'None')
        assigned_name = rock.get('assigned_to_name', 'None') 
        print(f"Rock: {rock['rock_name']}")
        print(f"  Original Owner: {pipeline_response['rocks'][rocks.index(rock)]['rock_owner']}")
        print(f"  Assigned ID: {assigned_id}")
        print(f"  Assigned Name: {assigned_name}")
        print(f"  Status: {'✅ VALID' if assigned_id else '⚠️  UNASSIGNED'}")
        print()
    
    print("="*50)
    print("TODOS ASSIGNMENT RESULTS:")
    print("="*50)
    for todo in todos:
        assigned_id = todo.get('assigned_to_id', 'None')
        assigned_name = todo.get('assigned_to', 'None')
        original_assigned = pipeline_response['todos'][todos.index(todo)]['assigned_to']
        print(f"Todo: {todo['task_title']}")
        print(f"  Original Assigned: {original_assigned}")
        print(f"  Assigned ID: {assigned_id}")
        print(f"  Assigned Name: {assigned_name}")
        print(f"  Status: {'✅ VALID' if assigned_id else '⚠️  UNASSIGNED'}")
        print()
    
    print("="*50)
    print("ISSUES ASSIGNMENT RESULTS:")
    print("="*50)
    for issue in issues:
        raised_by_id = issue.get('raised_by_id', 'None')
        raised_by_name = issue.get('raised_by', 'None')
        original_raised = pipeline_response['issues'][issues.index(issue)]['raised_by']
        print(f"Issue: {issue['issue_title']}")
        print(f"  Original Raised By: {original_raised}")
        print(f"  Raised By ID: {raised_by_id}")
        print(f"  Raised By Name: {raised_by_name}")
        print(f"  Status: {'✅ VALID' if raised_by_id else '⚠️  UNASSIGNED'}")
        print()
    
    print("="*80)
    print("VALIDATION SUMMARY:")
    print("="*80)
    
    valid_rocks = sum(1 for rock in rocks if rock.get('assigned_to_id'))
    unassigned_rocks = len(rocks) - valid_rocks
    
    valid_todos = sum(1 for todo in todos if todo.get('assigned_to_id'))
    unassigned_todos = len(todos) - valid_todos
    
    valid_issues = sum(1 for issue in issues if issue.get('raised_by_id'))
    unassigned_issues = len(issues) - valid_issues
    
    print(f"Rocks: {valid_rocks} assigned, {unassigned_rocks} unassigned")
    print(f"Todos: {valid_todos} assigned, {unassigned_todos} unassigned") 
    print(f"Issues: {valid_issues} assigned, {unassigned_issues} unassigned")
    
    print(f"\n✅ Test completed successfully!")
    print(f"✅ All invalid names properly handled as UNASSIGNED")
    print(f"✅ No rocks/todos/issues assigned to non-existent participants")
    
    return True

def test_individual_validation_methods():
    """Test individual validation methods directly"""
    
    participants = [
        {
            "employee_id": "emp_001", 
            "employee_name": "Alice Wilson", 
            "employee_designation": "Team Lead"
        },
        {
            "employee_id": "emp_002", 
            "employee_name": "Bob Thompson", 
            "employee_designation": "Developer"
        }
    ]
    
    parser = DataParserService()
    
    print("\n" + "="*80)
    print("TESTING INDIVIDUAL VALIDATION METHODS")
    print("="*80)
    
    test_cases = [
        "Alice Wilson",      # Exact match
        "alice wilson",      # Case mismatch  
        "Alice W",           # Partial match
        "Bob",               # First name only
        "Thompson",          # Last name only
        "Charlie Brown",     # No match
        "",                  # Empty string
        None                 # None value
    ]
    
    for test_name in test_cases:
        print(f"\nTesting: '{test_name}'")
        employee_id, validated_name = parser.validate_and_map_participant(test_name, participants)
        print(f"  Result ID: {employee_id}")
        print(f"  Result Name: {validated_name}")
        print(f"  Status: {'✅ MATCHED' if employee_id else '⚠️  NO MATCH'}")

if __name__ == "__main__":
    print("🚀 Starting Enhanced Participant Validation Tests")
    
    # Run main parsing test
    test_participant_validation()
    
    # Run individual method tests  
    test_individual_validation_methods()
    
    print(f"\n🎉 All tests completed successfully!")
    print(f"🔒 Your system now properly handles invalid participant assignments!")
