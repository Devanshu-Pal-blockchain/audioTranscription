"""
Simple test to verify session summary implementation in the quarter model and service.
"""

# Test 1: Verify Quarter model has session_summary field
print("🧪 Testing Quarter model...")
try:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    
    from models.quarter import Quarter
    
    # Create a test quarter instance
    test_quarter = Quarter(
        quarter="Q1",
        weeks=12,
        year=2024,
        title="Test Quarter",
        description="Test quarter for session summary",
        session_summary="This is a test session summary"
    )
    
    print("✅ Quarter model successfully created with session_summary")
    print(f"   Session Summary: {test_quarter.session_summary}")
    
    # Test model_dump includes session_summary
    quarter_dict = test_quarter.model_dump()
    if 'session_summary' in quarter_dict:
        print("✅ session_summary field included in model_dump()")
    else:
        print("❌ session_summary field missing from model_dump()")
        
except Exception as e:
    print(f"❌ Quarter model test failed: {str(e)}")

print("\n" + "="*50)

# Test 2: Verify import structure
print("🧪 Testing import structure...")
try:
    from service.quarter_service import QuarterService
    print("✅ QuarterService import successful")
    
    from service.data_parser_service import DataParserService
    print("✅ DataParserService import successful")
    
    from service.script_pipeline_service import ScriptPipelineService
    print("✅ ScriptPipelineService import successful")
    
except Exception as e:
    print(f"❌ Import test failed: {str(e)}")

print("\n" + "="*50)

# Test 3: Check if session_summary field exists in data_parser_service
print("🧪 Testing DataParserService session_summary integration...")
try:
    import inspect
    from service.data_parser_service import DataParserService
    
    # Check if methods have been updated to accept session_summary
    parser_service = DataParserService()
    
    # Check insert_to_db method signature
    insert_to_db_sig = inspect.signature(parser_service.insert_to_db)
    if 'session_summary' in insert_to_db_sig.parameters:
        print("✅ insert_to_db method has session_summary parameter")
    else:
        print("❌ insert_to_db method missing session_summary parameter")
    
    # Check save_parsed_data method signature  
    save_parsed_data_sig = inspect.signature(parser_service.save_parsed_data)
    if 'session_summary' in save_parsed_data_sig.parameters:
        print("✅ save_parsed_data method has session_summary parameter")
    else:
        print("❌ save_parsed_data method missing session_summary parameter")
        
    # Check if _save_session_summary_to_quarter method exists
    if hasattr(parser_service, '_save_session_summary_to_quarter'):
        print("✅ _save_session_summary_to_quarter method exists")
    else:
        print("❌ _save_session_summary_to_quarter method missing")
        
except Exception as e:
    print(f"❌ DataParserService test failed: {str(e)}")

print("\n🎉 Basic implementation verification completed!")
