"""
Quick test script to verify Gemini pipeline service is working correctly
"""
import sys
import os
import asyncio
import json

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_gemini_service():
    """Test the Gemini pipeline service components"""
    
    print("🚀 Testing Gemini Pipeline Service")
    print("=" * 50)
    
    # Test 1: Import the new service
    try:
        from service.script_gemini_pipeline_service import PipelineService, run_pipeline_for_transcript
        print("✅ Successfully imported Gemini pipeline service")
    except ImportError as e:
        print(f"❌ Failed to import Gemini service: {e}")
        return False
    
    # Test 2: Check environment variables
    try:
        gemini_key = os.getenv("GEMINI_API_KEY_SCRIPT")
        gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        
        if not gemini_key:
            print("❌ GEMINI_API_KEY_SCRIPT not found in environment")
            return False
        else:
            print(f"✅ Gemini API key found (ends with: ...{gemini_key[-6:]})")
            print(f"✅ Gemini model: {gemini_model}")
    except Exception as e:
        print(f"❌ Environment variable check failed: {e}")
        return False
    
    # Test 3: Initialize pipeline service
    try:
        pipeline = PipelineService()
        print("✅ Successfully initialized PipelineService")
    except Exception as e:
        print(f"❌ Failed to initialize PipelineService: {e}")
        return False
    
    # Test 4: Test Gemini model connection
    try:
        test_prompt = "Hello, this is a test. Please respond with 'Gemini service is working correctly.'"
        response = pipeline.gemini_model.generate_content(test_prompt)
        if response and response.text:
            print(f"✅ Gemini model connection successful")
            print(f"   Response: {response.text[:100]}...")
        else:
            print("❌ Gemini model returned empty response")
            return False
    except Exception as e:
        print(f"❌ Gemini model connection failed: {e}")
        return False
    
    # Test 5: Test participant CSV generation
    try:
        test_participants = [
            {
                "employee_id": "emp_001",
                "employee_name": "John Smith",
                "employee_designation": "Project Manager",
                "employee_responsibilities": "Team leadership"
            },
            {
                "employee_id": "emp_002", 
                "employee_name": "Sarah Johnson",
                "employee_designation": "Senior Developer",
                "employee_responsibilities": "Software development"
            }
        ]
        
        csv_output = pipeline.participants_to_csv(test_participants)
        expected_lines = 3  # Header + 2 participants
        actual_lines = len(csv_output.split('\n'))
        
        if actual_lines == expected_lines:
            print("✅ Participant CSV generation working correctly")
        else:
            print(f"❌ Participant CSV generation issue: expected {expected_lines} lines, got {actual_lines}")
            return False
            
    except Exception as e:
        print(f"❌ Participant CSV generation failed: {e}")
        return False
    
    # Test 6: Test semantic tokenization with sample transcript
    try:
        sample_transcript = {
            "full_transcript": "John Smith discussed the quarterly goals. Sarah Johnson will handle the development tasks. We need to complete the project by March 15th.",
            "quality_metrics": {"overall_confidence": 0.95}
        }
        
        semantic_data = pipeline.semantic_tokenization(sample_transcript)
        
        if semantic_data and "semantic_tokens" in semantic_data:
            print(f"✅ Semantic tokenization working correctly")
            print(f"   Generated {len(semantic_data['semantic_tokens'])} semantic tokens")
        else:
            print("❌ Semantic tokenization failed")
            return False
            
    except Exception as e:
        print(f"❌ Semantic tokenization failed: {e}")
        return False
    
    # Test 7: Test a small end-to-end pipeline with transcript
    try:
        print("\n🧪 Testing small end-to-end pipeline...")
        
        test_transcript = {
            "full_transcript": """
            Welcome to our quarterly planning meeting. John Smith, our Project Manager, will be leading the 
            initiatives this quarter. Sarah Johnson, Senior Developer, will focus on the technical implementation.
            
            Our main objectives are:
            1. Improve customer satisfaction by 15% this quarter
            2. Complete the mobile app development by March 30th
            3. Implement automated testing framework
            
            John will coordinate with the team weekly. Sarah will provide technical updates bi-weekly.
            """,
            "quality_metrics": {"overall_confidence": 0.9}
        }
        
        # Run a mini pipeline
        result = await run_pipeline_for_transcript(
            test_transcript, 
            num_weeks=4, 
            quarter_id="test_quarter_123",
            participants=test_participants
        )
        
        if result and "error" not in result:
            print("✅ End-to-end pipeline test successful")
            if "rocks" in result:
                print(f"   Generated {len(result['rocks'])} rocks")
            if "session_summary" in result:
                print(f"   Session summary: {result['session_summary'][:100]}...")
        else:
            error_msg = result.get("error", "Unknown error") if result else "No result returned"
            print(f"❌ End-to-end pipeline test failed: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ End-to-end pipeline test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Gemini Pipeline Service is ready for use.")
    print("\nNext steps:")
    print("1. Test with real audio uploads via the API")
    print("2. Monitor response times and quality")
    print("3. Check logs for any warnings or errors")
    print("4. Verify participant validation is working correctly")
    
    return True

if __name__ == "__main__":
    print("Starting Gemini Pipeline Service Test...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the test
    try:
        result = asyncio.run(test_gemini_service())
        if result:
            print("\n✅ Test completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Test failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        sys.exit(1)
