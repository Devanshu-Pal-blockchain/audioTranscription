"""
Test script to validate the enhanced recording implementation
"""

def test_id_generator():
    """Test the ID generator utility"""
    try:
        from utils.id_generator import generate_random_id, generate_session_id, generate_chunk_id
        
        # Test random ID generation
        id1 = generate_random_id()
        id2 = generate_random_id()
        print(f"✓ Random IDs generated: {id1}, {id2}")
        assert id1 != id2, "IDs should be unique"
        assert len(id1) == 8, "ID should be 8 characters"
        
        # Test session ID generation
        session_id = generate_session_id()
        print(f"✓ Session ID generated: {session_id}")
        assert session_id.startswith("SESSION_"), "Session ID should have SESSION_ prefix"
        
        # Test chunk ID generation
        chunk_id = generate_chunk_id(session_id, 1)
        print(f"✓ Chunk ID generated: {chunk_id}")
        assert "_CHUNK_001" in chunk_id, "Chunk ID should contain chunk number"
        
        print("✅ ID Generator tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ ID Generator test failed: {e}")
        return False

def test_recording_routes():
    """Test that recording routes can be imported"""
    try:
        from routes.recording import router, active_recording_sessions
        
        print("✓ Recording routes imported successfully")
        print(f"✓ Active sessions storage initialized: {type(active_recording_sessions)}")
        print(f"✓ Router object created: {type(router)}")
        
        print("✅ Recording routes tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Recording routes test failed: {e}")
        return False

def test_pipeline_service():
    """Test that pipeline service has the new transcribe_audio method"""
    try:
        from service.script_pipeline_service import PipelineService
        
        # Create pipeline instance
        pipeline = PipelineService("test_facilitator")
        
        # Check if transcribe_audio method exists
        assert hasattr(pipeline, 'transcribe_audio'), "transcribe_audio method should exist"
        print("✓ PipelineService has transcribe_audio method")
        
        print("✅ Pipeline service tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Pipeline service test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Enhanced Recording Implementation Tests\n")
    
    results = []
    
    print("1. Testing ID Generator...")
    results.append(test_id_generator())
    print()
    
    print("2. Testing Recording Routes...")
    results.append(test_recording_routes())
    print()
    
    print("3. Testing Pipeline Service...")
    results.append(test_pipeline_service())
    print()
    
    if all(results):
        print("🎉 All tests passed! Enhanced recording implementation is ready.")
        print("\nNext steps:")
        print("1. Start the FastAPI server: uvicorn main:app --reload")
        print("2. Start the frontend: npm run dev")
        print("3. Test the recording functionality in the browser")
    else:
        print("❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
