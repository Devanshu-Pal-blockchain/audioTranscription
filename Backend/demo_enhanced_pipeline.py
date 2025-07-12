"""
Quick demonstration of the enhanced pipeline service
Run this to test the improvements with your transcript data
"""

import asyncio
import json
import os
from typing import Dict, Any

async def demo_enhanced_pipeline():
    """Demonstrate the enhanced pipeline with your transcript"""
    
    # Load your transcript (modify path as needed)
    transcript_file = "transcripts.json"  # Update this path
    
    if os.path.exists(transcript_file):
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
    else:
        # Use the provided sample
        transcript_data = {
            "full_transcript": "okay good morning everyone let's get going we've got a lot to cover today first quick reminder the team offsite has been moved to the 26th and will now be at the indigo center not the old office space please update your calendars now diving into quarterly priorities our main rocks remain the same launch the workflow automation module reduce customer onboarding time by 25 percent and finish SOC 2 phase one by quarter end so let's start with metrics Divya Iyer noted that our churn rate for SMB customers has increased slightly to 6.3 percent which is higher than our 5 percent target Rahul Khanna added that the product demo completion rate dropped as well especially for mobile users there's some confusion with the new tour feature it might not be loading correctly on Android devices Karan Malhotra jumped in saying QA is already investigating it but they'll need help from frontend team to reproduce the bug so we agreed to assign that as a short-term fix by Friday Rahul will coordinate with the devs Neha Bansal brought up the delay in onboarding guides she mentioned that the updated PDF was due two weeks ago and new CS hires are struggling without it Priya Nair confirmed that the content team has the draft but it's not finalized we'll make it a to-do for this week deadline is next Wednesday also in the sales pipeline we're seeing good volume but lead-to-close time is slipping from 19 to 24 days Rahul said he thinks the qualification step is too loose we're letting in leads that aren't ready maybe need to revisit the MQL scoring model Divya agreed and said she'd audit the last 30 closed-lost deals by the end of this week to identify trends Karan brought up a technical concern the new audit logging service is consuming more memory than expected it's not a blocker yet but might affect scale if we don't handle it soon we'll flag it as a potential rock dependency Ankit Sharma mentioned that SOC 2 readiness is behind schedule the employee security training hasn't been rolled out yet Neha said she had it on her radar and will finalize the LMS content by Monday and send it for internal testing we also discussed the confusion around PTO requests last week apparently the form link was broken again HR will patch that this afternoon a customer story Neha shared that a major client appreciated our recent dashboard enhancements and wants to be part of a future beta round for the insights module Rahul asked whether we could include them in the September pilot group Karan said yes technically it's feasible we just need a final go-ahead by mid August to make the cut marketing is still waiting on final messaging for the Q3 campaign Rahul promised to send the approved language by Thursday also a reminder from Divya to clean up test users from the analytics workspace it's skewing NPS tracking data Ankit will take care of that as part of this sprint okay let's wrap up Neha will own the onboarding guide update Rahul will handle mobile bug coordination and campaign messaging Divya to audit closed-lost leads and Karan to review audit logging footprint Ankit to finalize SOC 2 training everyone please report progress by Friday EOD that's it for now good alignment team let's get back to execution"
        }
    
    # Sample participants (customize for your team)
    participants = [
        {
            "employee_name": "Divya Iyer",
            "employee_designation": "Product Manager",
            "employee_responsibilities": "Product strategy, customer metrics, user experience optimization"
        },
        {
            "employee_name": "Rahul Khanna", 
            "employee_designation": "Engineering Lead",
            "employee_responsibilities": "Technical architecture, development coordination, system performance"
        },
        {
            "employee_name": "Karan Malhotra",
            "employee_designation": "QA Manager",
            "employee_responsibilities": "Quality assurance, testing automation, system reliability"
        },
        {
            "employee_name": "Neha Bansal",
            "employee_designation": "Customer Success Manager", 
            "employee_responsibilities": "Customer onboarding, support processes, training materials"
        },
        {
            "employee_name": "Priya Nair",
            "employee_designation": "Content Manager",
            "employee_responsibilities": "Documentation, content creation, marketing materials"
        },
        {
            "employee_name": "Ankit Sharma",
            "employee_designation": "DevOps Engineer",
            "employee_responsibilities": "Infrastructure, security compliance, system monitoring"
        }
    ]
    
    print("🚀 Enhanced Pipeline Service Demo")
    print(f"📄 Transcript length: {len(transcript_data['full_transcript'])} characters")
    print(f"👥 Team members: {len(participants)}")
    print("⚙️  Enhanced analysis with comprehensive ROCKS generation")
    print()
    
    try:
        # Import the enhanced pipeline
        from service.script_gemini_pipeline_service import run_pipeline_for_transcript
        
        # Run with enhanced settings
        result = await run_pipeline_for_transcript(
            transcript_json=transcript_data,
            num_weeks=12,  # Quarter planning
            quarter_id="Q3_2025", 
            participants=participants
        )
        
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return
        
        # Display results summary
        print("✅ Enhanced Pipeline Completed Successfully!")
        print("="*50)
        
        print(f"📊 COMPREHENSIVE RESULTS:")
        print(f"   • Issues identified: {len(result.get('issues', []))}")
        print(f"   • Runtime solutions: {len(result.get('runtime_solutions', []))}")
        print(f"   • Short-term TODOs: {len(result.get('todos', []))}")
        print(f"   • Strategic ROCKS: {len(result.get('rocks', []))}")
        
        # Show sample ROCKS
        if result.get('rocks'):
            print(f"\n🎯 SAMPLE STRATEGIC ROCKS:")
            for i, rock in enumerate(result['rocks'][:3], 1):
                print(f"   {i}. {rock.get('rock_owner', 'Unknown')} ({rock.get('designation', 'Unknown')})")
                print(f"      {rock.get('smart_rock', 'No description')[:80]}...")
        
        # Save results
        output_file = "enhanced_meeting_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Full analysis saved to: {output_file}")
        print("\n🎉 Enhanced pipeline demonstration complete!")
        print("The output now contains significantly more detail and strategic depth.")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running from the Backend directory with proper dependencies.")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(demo_enhanced_pipeline())
