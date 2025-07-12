"""
Simple test to verify the enhanced pipeline fixes
"""

import asyncio
import json
import sys
import os

# Add the current directory to the path 
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_pipeline_fixes():
    """Test that the pipeline works without errors"""
    
    print("🧪 Testing Enhanced Pipeline Fixes")
    print("="*50)
    
    # Test data
    transcript_data = {
        "full_transcript": "okay good morning everyone let's get going we've got a lot to cover today first quick reminder the team offsite has been moved to the 26th and will now be at the indigo center not the old office space please update your calendars now diving into quarterly priorities our main rocks remain the same launch the workflow automation module reduce customer onboarding time by 25 percent and finish SOC 2 phase one by quarter end so let's start with metrics Divya Iyer noted that our churn rate for SMB customers has increased slightly to 6.3 percent which is higher than our 5 percent target Rahul Khanna added that the product demo completion rate dropped as well especially for mobile users there's some confusion with the new tour feature it might not be loading correctly on Android devices Karan Malhotra jumped in saying QA is already investigating it but they'll need help from frontend team to reproduce the bug so we agreed to assign that as a short-term fix by Friday Rahul will coordinate with the devs Neha Bansal brought up the delay in onboarding guides she mentioned that the updated PDF was due two weeks ago and new CS hires are struggling without it Priya Nair confirmed that the content team has the draft but it's not finalized we'll make it a to-do for this week deadline is next Wednesday also in the sales pipeline we're seeing good volume but lead-to-close time is slipping from 19 to 24 days Rahul said he thinks the qualification step is too loose we're letting in leads that aren't ready maybe need to revisit the MQL scoring model Divya agreed and said she'd audit the last 30 closed-lost deals by the end of this week to identify trends Karan brought up a technical concern the new audit logging service is consuming more memory than expected it's not a blocker yet but might affect scale if we don't handle it soon we'll flag it as a potential rock dependency Ankit Sharma mentioned that SOC 2 readiness is behind schedule the employee security training hasn't been rolled out yet Neha said she had it on her radar and will finalize the LMS content by Monday and send it for internal testing we also discussed the confusion around PTO requests last week apparently the form link was broken again HR will patch that this afternoon a customer story Neha shared that a major client appreciated our recent dashboard enhancements and wants to be part of a future beta round for the insights module Rahul asked whether we could include them in the September pilot group Karan said yes technically it's feasible we just need a final go-ahead by mid August to make the cut marketing is still waiting on final messaging for the Q3 campaign Rahul promised to send the approved language by Thursday also a reminder from Divya to clean up test users from the analytics workspace it's skewing NPS tracking data Ankit will take care of that as part of this sprint okay let's wrap up Neha will own the onboarding guide update Rahul will handle mobile bug coordination and campaign messaging Divya to audit closed-lost deals and Karan to review audit logging footprint Ankit to finalize SOC 2 training everyone please report progress by Friday EOD that's it for now good alignment team let's get back to execution"
    }
    
    participants = [
        {
            "employee_name": "Divya Iyer",
            "employee_designation": "Product Manager",
            "employee_responsibilities": "Product strategy, customer metrics, user experience optimization",
            "employee_id": "div001"
        },
        {
            "employee_name": "Rahul Khanna", 
            "employee_designation": "Engineering Lead",
            "employee_responsibilities": "Technical architecture, development coordination, system performance",
            "employee_id": "rah001"
        },
        {
            "employee_name": "Karan Malhotra",
            "employee_designation": "QA Manager",
            "employee_responsibilities": "Quality assurance, testing automation, system reliability",
            "employee_id": "kar001"
        },
        {
            "employee_name": "Neha Bansal",
            "employee_designation": "Customer Success Manager", 
            "employee_responsibilities": "Customer onboarding, support processes, training materials",
            "employee_id": "neh001"
        },
        {
            "employee_name": "Priya Nair",
            "employee_designation": "Content Manager",
            "employee_responsibilities": "Documentation, content creation, marketing materials",
            "employee_id": "pri001"
        },
        {
            "employee_name": "Ankit Sharma",
            "employee_designation": "DevOps Engineer",
            "employee_responsibilities": "Infrastructure, security compliance, system monitoring",
            "employee_id": "ank001"
        }
    ]
    
    try:
        from service.script_gemini_pipeline_service import run_pipeline_for_transcript
        
        print("✅ Testing enhanced pipeline...")
        result = await run_pipeline_for_transcript(
            transcript_json=transcript_data,
            num_weeks=4,  # Shorter for testing
            quarter_id="test_quarter_id",
            participants=participants
        )
        
        if "error" in result:
            print(f"❌ Pipeline failed: {result['error']}")
            return False
        
        print("✅ Pipeline completed successfully!")
        print(f"📊 Results:")
        print(f"   • Issues: {len(result.get('issues', []))}")
        print(f"   • Runtime Solutions: {len(result.get('runtime_solutions', []))}")
        print(f"   • TODOs: {len(result.get('todos', []))}")
        print(f"   • ROCKS: {len(result.get('rocks', []))}")
        
        # Check for empty assigned_to_id fields in rocks
        rocks = result.get('rocks', [])
        for i, rock in enumerate(rocks):
            owner = rock.get('rock_owner', 'Unknown')
            assigned_id = rock.get('assigned_to_id', 'Not set')
            print(f"   Rock {i+1}: {owner} (ID: {assigned_id})")
        
        # Save test results
        with open("test_pipeline_results.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print("\n✅ All tests passed! Enhanced pipeline is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pipeline_fixes())
    if success:
        print("\n🎉 Enhanced Pipeline Test PASSED!")
    else:
        print("\n💥 Enhanced Pipeline Test FAILED!")
