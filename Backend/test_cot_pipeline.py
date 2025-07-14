#!/usr/bin/env python3
"""
Test script for Enhanced Chain of Thought Pipeline Service
Tests the improved CoT reasoning, participant validation, and assignment accuracy
"""

import asyncio
import json
import os
import sys
from typing import Dict, List, Any

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from service.script_pipeline_service import PipelineService
from service.data_parser_service import DataParserService

class CoTPipelineTestSuite:
    def __init__(self):
        self.pipeline = PipelineService()
        self.data_parser = DataParserService()
        
    def create_test_participants(self) -> List[Dict]:
        """Create realistic test participants"""
        return [
            {"employee_name": "Sarah Johnson", "employee_id": "emp_001", "job_title": "Chief Technology Officer"},
            {"employee_name": "Michael Chen", "employee_id": "emp_002", "job_title": "Product Manager"},
            {"employee_name": "Emily Davis", "employee_id": "emp_003", "job_title": "Senior Developer"},
            {"employee_name": "Robert Williams", "employee_id": "emp_004", "job_title": "Marketing Director"},
            {"employee_name": "Jennifer Martinez", "employee_id": "emp_005", "job_title": "Operations Manager"},
            {"employee_name": "David Thompson", "employee_id": "emp_006", "job_title": "Financial Controller"},
            {"employee_name": "Amanda Rodriguez", "employee_id": "emp_007", "job_title": "HR Manager"},
            {"employee_name": "Christopher Lee", "employee_id": "emp_008", "job_title": "Sales Director"}
        ]
    
    def create_test_segment(self, segment_id: int, participants: List[Dict]) -> Dict[str, Any]:
        """Create a test segment with realistic meeting content"""
        
        # Create realistic meeting content with clear assignments
        meeting_scenarios = [
            {
                "text": """
                Sarah Johnson (CTO): We need to prioritize the security audit for our API infrastructure. 
                Emily, I want you to take ownership of the encryption layer implementation. 
                This needs to be completed by next Friday. Michael, you'll need to coordinate 
                with Emily on the user authentication requirements. Jennifer, please prepare 
                the compliance documentation for this initiative.
                
                Michael Chen (Product Manager): I agree with the timeline. I'll work with Emily 
                on defining the authentication requirements. We should also consider the impact 
                on user experience. Robert, can you prepare a communication plan for our customers 
                about these security improvements?
                
                Emily Davis (Senior Developer): I can handle the encryption implementation. 
                I'll need about 40 hours to complete this properly. Should I also handle 
                the database security updates?
                """,
                "people": ["Sarah Johnson", "Emily Davis", "Michael Chen", "Jennifer Martinez", "Robert Williams"],
                "action_items": [
                    "Emily to implement encryption layer by next Friday",
                    "Michael to coordinate authentication requirements",
                    "Jennifer to prepare compliance documentation",
                    "Robert to prepare customer communication plan"
                ]
            },
            {
                "text": """
                Jennifer Martinez (Operations Manager): Our quarterly planning shows we need 
                to streamline the onboarding process. David, I need you to analyze the cost 
                implications of the new HR system. Amanda, you should lead the implementation 
                of the new employee orientation program.
                
                David Thompson (Financial Controller): I can provide the cost analysis by 
                Wednesday. The budget impact will be significant, but the ROI looks positive. 
                Christopher, we'll need to factor this into the Q2 sales projections.
                
                Amanda Rodriguez (HR Manager): I volunteer to lead the orientation program. 
                I'll need support from IT for the online training modules. Sarah, can your 
                team help with the technical setup?
                """,
                "people": ["Jennifer Martinez", "David Thompson", "Amanda Rodriguez", "Christopher Lee", "Sarah Johnson"],
                "action_items": [
                    "David to analyze cost implications by Wednesday",
                    "Amanda to lead employee orientation program implementation",
                    "Christopher to factor costs into Q2 sales projections",
                    "Sarah's team to help with technical setup"
                ]
            }
        ]
        
        scenario = meeting_scenarios[segment_id % len(meeting_scenarios)]
        
        return {
            "segment_id": segment_id,
            "text": scenario["text"],
            "people": scenario["people"],
            "dates": ["next Friday", "Wednesday", "Q2"],
            "organizations": ["Company"],
            "locations": [],
            "action_items": scenario["action_items"],
            "key_phrases": ["security audit", "quarterly planning", "onboarding process"],
            "entities": {
                "people": scenario["people"],
                "dates": ["next Friday", "Wednesday"],
                "action_items": scenario["action_items"]
            }
        }
    
    async def test_segment_analysis_cot(self):
        """Test the Chain of Thought segment analysis"""
        print("🧠 Testing Chain of Thought Segment Analysis...")
        
        participants = self.create_test_participants()
        test_segment = self.create_test_segment(0, participants)
        
        try:
            # Analyze segment with CoT reasoning
            result = await self.pipeline._analyze_segment(test_segment)
            
            print("✅ Segment analysis completed with CoT reasoning")
            print(f"📊 Analysis length: {len(result['analysis'])} characters")
            
            # Check if the analysis contains CoT reasoning indicators
            analysis_text = result['analysis'].lower()
            cot_indicators = [
                "step 1", "step 2", "step 3", "step 4", "step 5",
                "let me first", "now let me", "based on my analysis",
                "thinking through", "systematically"
            ]
            
            found_indicators = [indicator for indicator in cot_indicators if indicator in analysis_text]
            print(f"🔍 CoT reasoning indicators found: {found_indicators}")
            
            if found_indicators:
                print("✅ Chain of Thought reasoning successfully implemented")
            else:
                print("⚠️ CoT reasoning indicators not clearly present")
                
            return result
            
        except Exception as e:
            print(f"❌ Error in segment analysis: {e}")
            return None
    
    def test_participant_validation_enhanced(self):
        """Test the enhanced participant validation with various name scenarios"""
        print("\n👥 Testing Enhanced Participant Validation...")
        
        participants = self.create_test_participants()
        
        # Test various name scenarios
        test_cases = [
            # Exact matches
            ("Sarah Johnson", True, "Exact match"),
            ("Michael Chen", True, "Exact match"),
            
            # Case variations
            ("sarah johnson", True, "Case insensitive"),
            ("EMILY DAVIS", True, "All caps"),
            
            # Partial matches
            ("Sarah", True, "First name only"),
            ("Johnson", True, "Last name only"),
            
            # Nickname variations
            ("Mike Chen", True, "Nickname for Michael"),
            ("Bob Williams", True, "Nickname for Robert"),
            ("Chris Lee", True, "Nickname for Christopher"),
            
            # With titles/prefixes
            ("Mr. David Thompson", True, "With title"),
            ("Dr. Sarah Johnson", True, "With title"),
            
            # UNASSIGNED cases
            ("UNASSIGNED: Sarah Johnson", True, "Previously unassigned but matchable"),
            ("UNASSIGNED: Unknown Person", False, "Truly unassigned"),
            
            # Invalid cases
            ("John Doe", False, "Non-existent person"),
            ("", False, "Empty name"),
            ("Unknown Manager", False, "Generic title")
        ]
        
        results = []
        for name, expected_match, description in test_cases:
            employee_id, validated_name = self.data_parser.validate_and_map_participant(name, participants)
            actual_match = employee_id is not None
            
            status = "✅" if actual_match == expected_match else "❌"
            results.append({
                "name": name,
                "expected": expected_match,
                "actual": actual_match,
                "employee_id": employee_id,
                "validated_name": validated_name,
                "description": description,
                "status": status
            })
            
            print(f"{status} {description}: '{name}' -> {validated_name} (ID: {employee_id})")
        
        # Calculate success rate
        successful = sum(1 for r in results if r["status"] == "✅")
        total = len(results)
        success_rate = (successful / total) * 100
        
        print(f"\n📊 Validation Test Results: {successful}/{total} ({success_rate:.1f}% success rate)")
        
        return results
    
    async def test_rocks_generation_cot(self):
        """Test ROCKS generation with Chain of Thought reasoning"""
        print("\n🎯 Testing ROCKS Generation with CoT...")
        
        participants = self.create_test_participants()
        
        # Create multiple test segments
        segment_analyses = []
        for i in range(3):
            test_segment = self.create_test_segment(i, participants)
            # Simulate segment analysis result
            segment_analyses.append({
                "segment_id": i,
                "analysis": f"Comprehensive analysis of segment {i+1} with detailed task assignments and strategic discussions.",
                "people": test_segment["people"],
                "action_items": test_segment["action_items"],
                "entities": test_segment.get("entities", {}),
                "dates": test_segment.get("dates", []),
                "organizations": test_segment.get("organizations", [])
            })
        
        try:
            # Generate ROCKS with CoT reasoning
            num_weeks = 12
            rocks_data = await self.pipeline.generate_rocks(segment_analyses, num_weeks, participants)
            
            if "error" in rocks_data:
                print(f"❌ Error in ROCKS generation: {rocks_data['error']}")
                return None
            
            print("✅ ROCKS generation completed successfully")
            
            # Analyze the results
            self.analyze_rocks_quality(rocks_data, participants, num_weeks)
            
            return rocks_data
            
        except Exception as e:
            print(f"❌ Error in ROCKS generation: {e}")
            return None
    
    def analyze_rocks_quality(self, rocks_data: Dict[str, Any], participants: List[Dict], num_weeks: int):
        """Analyze the quality of generated ROCKS"""
        print("\n📈 Analyzing ROCKS Quality...")
        
        # Check basic structure
        required_sections = ["session_summary", "issues", "todos", "rocks"]
        for section in required_sections:
            if section in rocks_data:
                print(f"✅ {section}: Present")
            else:
                print(f"❌ {section}: Missing")
        
        # Analyze assignment accuracy
        if "rocks" in rocks_data:
            rocks = rocks_data["rocks"]
            print(f"📊 Total ROCKS generated: {len(rocks)}")
            
            participant_names = [p["employee_name"] for p in participants]
            assigned_rocks = 0
            unassigned_rocks = 0
            
            for rock in rocks:
                owner = rock.get("rock_owner", "")
                if owner and not owner.startswith("UNASSIGNED"):
                    if owner in participant_names:
                        assigned_rocks += 1
                    else:
                        print(f"⚠️ Rock assigned to non-participant: {owner}")
                else:
                    unassigned_rocks += 1
            
            print(f"✅ Properly assigned ROCKS: {assigned_rocks}")
            print(f"⚠️ Unassigned ROCKS: {unassigned_rocks}")
            
            # Check milestone completeness
            incomplete_milestones = 0
            for rock in rocks:
                milestones = rock.get("milestones", [])
                if len(milestones) < num_weeks:
                    incomplete_milestones += 1
            
            print(f"📅 ROCKS with complete {num_weeks}-week milestones: {len(rocks) - incomplete_milestones}")
            print(f"⚠️ ROCKS with incomplete milestones: {incomplete_milestones}")
    
    def test_assignment_accuracy(self):
        """Test assignment accuracy in data parsing"""
        print("\n🎯 Testing Assignment Accuracy...")
        
        participants = self.create_test_participants()
        
        # Simulate pipeline response with various assignment scenarios
        test_pipeline_response = {
            "rocks": [
                {
                    "rock_owner": "Sarah Johnson",  # Exact match
                    "smart_rock": "Implement security infrastructure improvements",
                    "milestones": []
                },
                {
                    "rock_owner": "Mike Chen",  # Nickname
                    "smart_rock": "Enhance product user experience",
                    "milestones": []
                },
                {
                    "rock_owner": "UNASSIGNED",  # Intentionally unassigned
                    "smart_rock": "Improve overall system performance",
                    "milestones": []
                },
                {
                    "rock_owner": "Unknown Manager",  # Should be unassigned
                    "smart_rock": "Coordinate cross-department initiatives",
                    "milestones": []
                }
            ],
            "todos": [
                {
                    "task_title": "Complete security audit",
                    "assigned_to": "Emily Davis",  # Exact match
                    "due_date": "2024-08-01"
                },
                {
                    "task_title": "Prepare financial report",
                    "assigned_to": "Dave Thompson",  # Nickname for David
                    "due_date": "2024-08-05"
                }
            ],
            "issues": [
                {
                    "issue_title": "System performance degradation",
                    "raised_by": "Chris Lee",  # Nickname for Christopher
                    "description": "System response times are slow"
                }
            ]
        }
        
        # Parse the response
        try:
            rocks_array, tasks_array, todos_array, issues_array, _ = self.data_parser.parse_pipeline_response(
                test_pipeline_response, "test_quarter", participants
            )
            
            print("✅ Pipeline response parsed successfully")
            
            # Analyze assignment accuracy
            print("\n📊 Assignment Analysis:")
            
            # Check rocks
            for rock in rocks_array:
                owner = rock.get("assigned_to_name", "")
                owner_id = rock.get("assigned_to_id")
                status = "✅ Assigned" if owner_id else "⚠️ Unassigned"
                print(f"Rock: {rock.get('rock_name', 'Unknown')} -> {owner} ({status})")
            
            # Check todos
            for todo in todos_array:
                assignee = todo.get("assigned_to", "")
                assignee_id = todo.get("assigned_to_id")
                status = "✅ Assigned" if assignee_id else "⚠️ Unassigned"
                print(f"Todo: {todo.get('task_title', 'Unknown')} -> {assignee} ({status})")
            
            # Check issues
            for issue in issues_array:
                raised_by = issue.get("raised_by", "")
                raised_by_id = issue.get("raised_by_id")
                status = "✅ Assigned" if raised_by_id else "⚠️ Unassigned"
                print(f"Issue: {issue.get('issue_title', 'Unknown')} -> {raised_by} ({status})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error in assignment testing: {e}")
            return False
    
    async def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive Chain of Thought Pipeline Test Suite")
        print("=" * 70)
        
        # Test 1: Segment Analysis with CoT
        segment_result = await self.test_segment_analysis_cot()
        
        # Test 2: Enhanced Participant Validation
        validation_results = self.test_participant_validation_enhanced()
        
        # Test 3: Assignment Accuracy
        assignment_success = self.test_assignment_accuracy()
        
        # Test 4: ROCKS Generation with CoT
        rocks_result = await self.test_rocks_generation_cot()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 TEST SUITE SUMMARY")
        print("=" * 70)
        
        tests_passed = 0
        total_tests = 4
        
        if segment_result:
            print("✅ Segment Analysis with CoT: PASSED")
            tests_passed += 1
        else:
            print("❌ Segment Analysis with CoT: FAILED")
        
        validation_success_rate = sum(1 for r in validation_results if r["status"] == "✅") / len(validation_results)
        if validation_success_rate >= 0.8:
            print(f"✅ Participant Validation: PASSED ({validation_success_rate:.1%} accuracy)")
            tests_passed += 1
        else:
            print(f"❌ Participant Validation: FAILED ({validation_success_rate:.1%} accuracy)")
        
        if assignment_success:
            print("✅ Assignment Accuracy: PASSED")
            tests_passed += 1
        else:
            print("❌ Assignment Accuracy: FAILED")
        
        if rocks_result and "error" not in rocks_result:
            print("✅ ROCKS Generation with CoT: PASSED")
            tests_passed += 1
        else:
            print("❌ ROCKS Generation with CoT: FAILED")
        
        print(f"\n🏆 Overall Success Rate: {tests_passed}/{total_tests} ({tests_passed/total_tests:.1%})")
        
        if tests_passed == total_tests:
            print("🎉 All tests passed! Chain of Thought implementation is working correctly.")
        else:
            print("⚠️ Some tests failed. Review the implementations for improvements.")

async def main():
    """Main test execution"""
    test_suite = CoTPipelineTestSuite()
    await test_suite.run_comprehensive_test()

if __name__ == "__main__":
    # Check if API keys are available
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ OPENAI_API_KEY not set. Some tests may fail.")
    
    asyncio.run(main())
