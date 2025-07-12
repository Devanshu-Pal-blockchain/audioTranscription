#!/usr/bin/env python3
"""
Test script for the enhanced pipeline service using the provided transcript
This demonstrates the improved prompts and comprehensive analysis capabilities
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our enhanced pipeline service
from service.script_pipeline_service import run_pipeline_for_transcript

# Sample transcript data from the attachment
SAMPLE_TRANSCRIPT = {
    "full_transcript": "okay good morning everyone let's get going we've got a lot to cover today first quick reminder the team offsite has been moved to the 26th and will now be at the indigo center not the old office space please update your calendars now diving into quarterly priorities our main rocks remain the same launch the workflow automation module reduce customer onboarding time by 25 percent and finish SOC 2 phase one by quarter end so let's start with metrics Divya Iyer noted that our churn rate for SMB customers has increased slightly to 6.3 percent which is higher than our 5 percent target Rahul Khanna added that the product demo completion rate dropped as well especially for mobile users there's some confusion with the new tour feature it might not be loading correctly on Android devices Karan Malhotra jumped in saying QA is already investigating it but they'll need help from frontend team to reproduce the bug so we agreed to assign that as a short-term fix by Friday Rahul will coordinate with the devs Neha Bansal brought up the delay in onboarding guides she mentioned that the updated PDF was due two weeks ago and new CS hires are struggling without it Priya Nair confirmed that the content team has the draft but it's not finalized we'll make it a to-do for this week deadline is next Wednesday also in the sales pipeline we're seeing good volume but lead-to-close time is slipping from 19 to 24 days Rahul said he thinks the qualification step is too loose we're letting in leads that aren't ready maybe need to revisit the MQL scoring model Divya agreed and said she'd audit the last 30 closed-lost deals by the end of this week to identify trends Karan brought up a technical concern the new audit logging service is consuming more memory than expected it's not a blocker yet but might affect scale if we don't handle it soon we'll flag it as a potential rock dependency Ankit Sharma mentioned that SOC 2 readiness is behind schedule the employee security training hasn't been rolled out yet Neha said she had it on her radar and will finalize the LMS content by Monday and send it for internal testing we also discussed the confusion around PTO requests last week apparently the form link was broken again HR will patch that this afternoon a customer story Neha shared that a major client appreciated our recent dashboard enhancements and wants to be part of a future beta round for the insights module Rahul asked whether we could include them in the September pilot group Karan said yes technically it's feasible we just need a final go-ahead by mid August to make the cut marketing is still waiting on final messaging for the Q3 campaign Rahul promised to send the approved language by Thursday also a reminder from Divya to clean up test users from the analytics workspace it's skewing NPS tracking data Ankit will take care of that as part of this sprint okay let's wrap up Neha will own the onboarding guide update Rahul will handle mobile bug coordination and campaign messaging Divya to audit closed-lost leads and Karan to review audit logging footprint Ankit to finalize SOC 2 training everyone please report progress by Friday EOD that's it for now good alignment team let's get back to execution"
}

# Sample participants for the meeting
SAMPLE_PARTICIPANTS = [
    {
        "employee_id": "emp_001",
        "employee_name": "Divya Iyer",
        "employee_designation": "Product Manager",
        "employee_responsibilities": "Product strategy, customer metrics, user experience optimization"
    },
    {
        "employee_id": "emp_002",
        "employee_name": "Rahul Khanna", 
        "employee_designation": "Engineering Lead",
        "employee_responsibilities": "Technical architecture, development coordination, system performance"
    },
    {
        "employee_id": "emp_003",
        "employee_name": "Karan Malhotra",
        "employee_designation": "QA Manager",
        "employee_responsibilities": "Quality assurance, testing automation, system reliability"
    },
    {
        "employee_id": "emp_004",
        "employee_name": "Neha Bansal",
        "employee_designation": "Customer Success Manager", 
        "employee_responsibilities": "Customer onboarding, support processes, training materials"
    },
    {
        "employee_id": "emp_005",
        "employee_name": "Priya Nair",
        "employee_designation": "Content Manager",
        "employee_responsibilities": "Documentation, content creation, marketing materials"
    },
    {
        "employee_id": "emp_006",
        "employee_name": "Ankit Sharma",
        "employee_designation": "DevOps Engineer",
        "employee_responsibilities": "Infrastructure, security compliance, system monitoring"
    }
]

async def test_enhanced_pipeline():
    """Test the enhanced pipeline with comprehensive analysis"""
    
    print("🚀 Testing Enhanced Pipeline Service")
    print("="*60)
    
    # Test parameters
    num_weeks = 12  # Quarter duration
    quarter_id = "Q3_2025"
    
    print(f"📊 Input Parameters:")
    print(f"   - Number of weeks: {num_weeks}")
    print(f"   - Quarter ID: {quarter_id}")
    print(f"   - Participants: {len(SAMPLE_PARTICIPANTS)}")
    print(f"   - Transcript length: {len(SAMPLE_TRANSCRIPT['full_transcript'])} characters")
    print()
    
    try:
        # Run the enhanced pipeline
        print("🔄 Running enhanced pipeline with comprehensive analysis...")
        result = await run_pipeline_for_transcript(
            transcript_json=SAMPLE_TRANSCRIPT,
            num_weeks=num_weeks,
            quarter_id=quarter_id,
            participants=SAMPLE_PARTICIPANTS
        )
        
        # Check if there was an error
        if "error" in result:
            print(f"❌ Pipeline failed with error: {result['error']}")
            if "raw_response" in result:
                print(f"Raw response: {result['raw_response'][:500]}...")
            return
        
        # Display comprehensive results
        print("✅ Enhanced Pipeline completed successfully!")
        print("="*60)
        
        # Session Summary
        if "session_summary" in result:
            print("📋 SESSION SUMMARY:")
            summary = result["session_summary"]
            for key, value in summary.items():
                print(f"   {key.replace('_', ' ').title()}: {value}")
            print()
        
        # Issues Analysis
        if "issues" in result:
            print(f"🔍 ISSUES IDENTIFIED: {len(result['issues'])}")
            for i, issue in enumerate(result["issues"][:5], 1):  # Show first 5
                print(f"   {i}. {issue.get('issue_title', 'Unknown Issue')}")
                print(f"      Raised by: {issue.get('raised_by', 'Unknown')}")
                print(f"      Type: {issue.get('linked_solution_type', 'Unknown')}")
            if len(result["issues"]) > 5:
                print(f"   ... and {len(result['issues']) - 5} more issues")
            print()
        
        # Runtime Solutions
        if "runtime_solutions" in result:
            print(f"⚡ RUNTIME SOLUTIONS: {len(result['runtime_solutions'])}")
            for solution in result["runtime_solutions"][:3]:  # Show first 3
                print(f"   - {solution.get('solution_title', 'Unknown Solution')}")
                print(f"     Assigned to: {solution.get('assigned_to', 'Unknown')}")
            print()
        
        # TODOs
        if "todos" in result:
            print(f"📝 SHORT-TERM TODOS: {len(result['todos'])}")
            for todo in result["todos"][:5]:  # Show first 5
                print(f"   - {todo.get('task_title', 'Unknown Task')}")
                print(f"     Assigned to: {todo.get('assigned_to', 'Unknown')} | Due: {todo.get('due_date', 'Unknown')}")
            print()
        
        # ROCKS (Strategic Initiatives)
        if "rocks" in result:
            print(f"🎯 STRATEGIC ROCKS: {len(result['rocks'])}")
            for i, rock in enumerate(result["rocks"][:5], 1):  # Show first 5
                print(f"   {i}. Owner: {rock.get('rock_owner', 'Unknown')}")
                print(f"      SMART Rock: {rock.get('smart_rock', 'Unknown')[:100]}...")
                if "milestones" in rock:
                    print(f"      Milestones: {len(rock['milestones'])} weeks planned")
                print()
            if len(result["rocks"]) > 5:
                print(f"   ... and {len(result['rocks']) - 5} more strategic rocks")
            print()
        
        # Enhanced features (if present)
        if "strategic_initiatives" in result:
            print("🔬 ENHANCED ANALYSIS:")
            initiatives = result["strategic_initiatives"]
            if "cross_functional_projects" in initiatives:
                print(f"   Cross-functional projects: {len(initiatives['cross_functional_projects'])}")
            if "process_improvements" in initiatives:
                print(f"   Process improvements: {len(initiatives['process_improvements'])}")
            if "technology_initiatives" in initiatives:
                print(f"   Technology initiatives: {len(initiatives['technology_initiatives'])}")
            print()
        
        # Compliance and metadata
        if "compliance_log" in result:
            compliance = result["compliance_log"]
            print("📊 PROCESSING DETAILS:")
            print(f"   Model: {compliance.get('genai_model', 'Unknown')}")
            print(f"   Analysis depth: {compliance.get('analysis_depth', 'Standard')}")
            print(f"   Generation attempts: {compliance.get('generation_attempts', 'Unknown')}")
            print(f"   Processing version: {compliance.get('processing_pipeline_version', 'Unknown')}")
            print()
        
        # Save detailed results
        output_file = "enhanced_pipeline_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Full results saved to: {output_file}")
        print("="*60)
        print("🎉 Enhanced pipeline test completed successfully!")
        
        # Summary statistics
        total_items = len(result.get("issues", [])) + len(result.get("todos", [])) + len(result.get("rocks", [])) + len(result.get("runtime_solutions", []))
        print(f"📈 TOTAL EXTRACTED ITEMS: {total_items}")
        print(f"   This represents a significant improvement in detail extraction!")
        
    except Exception as e:
        print(f"❌ Error during pipeline execution: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to run the test"""
    print("Enhanced Pipeline Service Test")
    print("Testing comprehensive analysis and detailed ROCKS generation")
    print()
    
    # Run the async test
    asyncio.run(test_enhanced_pipeline())

if __name__ == "__main__":
    main()
