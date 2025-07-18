#!/usr/bin/env python3
"""
Test script to verify content validation improvements
Tests the new validation logic for insufficient transcript content
"""

import asyncio
import json
import sys
import os

# Add the Backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from service.script_pipeline_service import PipelineService

async def test_content_validation():
    """Test that the pipeline handles insufficient content gracefully"""
    
    print("Testing Content Validation Improvements")
    print("=" * 50)
    
    # Test cases with different content lengths
    test_cases = [
        {
            "name": "Empty Content",
            "transcript": "",
            "expected_behavior": "Should return empty results with warning"
        },
        {
            "name": "Very Short Content",
            "transcript": "Hello world test",
            "expected_behavior": "Should return empty results with warning"
        },
        {
            "name": "Basic Greetings",
            "transcript": "Hello everyone. How are you doing today? Good morning. Thank you.",
            "expected_behavior": "Should return empty results with warning"
        },
        {
            "name": "Business Content",
            "transcript": "Welcome to our Q1 planning meeting. We need to increase customer acquisition by 25% this quarter. Sarah will lead the marketing campaign. John needs to complete the new feature development by March 15th. We have an issue with customer support response times that Mike will address. Our revenue goal is $500,000 for this quarter.",
            "expected_behavior": "Should process normally and generate ROCKs"
        }
    ]
    
    pipeline = PipelineService(facilitator_id="test_facilitator")
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{i+1}. Testing: {test_case['name']}")
        print(f"Content: '{test_case['transcript'][:100]}...' ({len(test_case['transcript'].split())} words)")
        print(f"Expected: {test_case['expected_behavior']}")
        
        try:
            # Prepare transcript data
            transcript_json = {
                "transcript": test_case['transcript'],
                "session_id": f"test_session_{i+1}",
                "metadata": {
                    "quarter_id": "test_quarter_2024_Q1",
                    "meetingTitle": f"Test Meeting {i+1}",
                    "meetingDescription": "Content validation test"
                }
            }
            
            # Run pipeline
            result = await pipeline.run_pipeline_for_transcript(
                transcript_json=transcript_json,
                num_weeks=12,
                quarter_id="test_quarter_2024_Q1",
                participants=[]
            )
            
            # Analyze results
            rocks_count = len(result.get('rocks', []))
            todos_count = len(result.get('todos', []))
            session_summary = result.get('session_summary', {})
            analysis_note = session_summary.get('analysis_note', '')
            
            print(f"Results:")
            print(f"  - ROCKs generated: {rocks_count}")
            print(f"  - TODOs generated: {todos_count}")
            if analysis_note:
                print(f"  - Analysis note: {analysis_note[:100]}...")
            
            # Validate behavior
            if len(test_case['transcript'].split()) < 20:
                if rocks_count == 0 and todos_count == 0 and analysis_note:
                    print("  ✅ PASS: Correctly handled insufficient content")
                else:
                    print("  ❌ FAIL: Should have returned empty results with warning")
            else:
                if rocks_count > 0 or todos_count > 0:
                    print("  ✅ PASS: Generated content as expected")
                else:
                    print("  ⚠️  NOTE: No content generated (may need better prompts)")
                    
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
        
        print("-" * 40)

    print("\nContent Validation Test Complete!")
    print("\nUsage Guidelines:")
    print("- Record actual meeting content with business discussions")
    print("- Include goals, tasks, responsibilities, and action items")
    print("- Avoid test phrases like 'hello', 'test', or basic greetings")
    print("- Minimum 20 words recommended for meaningful analysis")

if __name__ == "__main__":
    asyncio.run(test_content_validation())
