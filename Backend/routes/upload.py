"""
Upload routes for audio files and CSV data
"""

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
import asyncio
from typing import Optional
from dotenv import load_dotenv
from models.user import User
from service.auth_service import admin_required
from service.script_pipeline_service import run_pipeline_for_audio
from service.data_parser_service import parse_pipeline_response_to_files

load_dotenv()

router = APIRouter()

from fastapi import Form

@router.post("/upload-audio")
async def upload_audio(
    file: UploadFile = File(...),
    quarter_id: Optional[str] = None,
    meetingTitle: Optional[str] = Form(None),
    meetingDescription: Optional[str] = Form(None),
    quarter: Optional[str] = Form(None),
    quarterYear: Optional[str] = Form(None),
    quarterWeeks: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    year: Optional[str] = Form(None),
    participants: Optional[str] = Form(None),
    id: Optional[str] = Form(None),
    quarter_id_form: Optional[str] = Form(None),
    created_at: Optional[str] = Form(None),
    updated_at: Optional[str] = Form(None),
    current_user: User = Depends(admin_required)
):
    """
    Upload and process audio file to generate rocks and tasks
    
    Args:
        file: Audio file to process
        quarter_id: Optional quarter ID to associate rocks with
        current_user: Current authenticated admin user
        
    Returns:
        Dict with upload status and pipeline information
    """
    # Validate file extension
    allowed_exts = [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".webm"]
    if not file.filename or not any(file.filename.endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail="Only audio files are allowed.")

    # Print all received quarter details for debugging
    print("--- Quarter Details Received with Audio Upload ---")
    print({
        'meetingTitle': meetingTitle,
        'meetingDescription': meetingDescription,
        'quarter': quarter,
        'quarterYear': quarterYear,
        'quarterWeeks': quarterWeeks,
        'status': status,
        'title': title,
        'description': description,
        'year': year,
        'participants': participants,
        'id': id,
        'quarter_id': quarter_id_form,
        'created_at': created_at,
        'updated_at': updated_at,
    })
    print("--- End Quarter Details ---")
    
    # Save file to disk
    file_location = f"uploaded_audios/{file.filename}"
    os.makedirs(os.path.dirname(file_location), exist_ok=True)
    with open(file_location, "wb") as f:
        f.write(await file.read())
    
    # Start pipeline in background (non-blocking)
    async def process_audio_background():
        try:
            # Check if test.csv exists
            if not os.path.exists("test.csv"):
                print("Warning: test.csv file not found (required for ROCKS generation)")
                return
            
            # Run pipeline with default 12 weeks
            result = await run_pipeline_for_audio(
                file_location, 
                num_weeks=12, 
                admin_id=str(current_user.employee_id)
            )
            
            if "error" in result:
                print(f"Pipeline failed: {result['error']}")
            else:
                print("Pipeline completed successfully!")
                
                # Save to files if quarter_id provided
                if quarter_id:
                    rocks_file, tasks_file = parse_pipeline_response_to_files(result)
                    if rocks_file and tasks_file:
                        print(f"Data saved to files: {rocks_file}, {tasks_file}")
                    else:
                        print("Failed to save data to files")
                
        except Exception as e:
            print(f"Background pipeline error: {e}")
        finally:
            # Clean up audio file
            try:
                os.remove(file_location)
            except:
                pass
    
    asyncio.create_task(process_audio_background())
    
    return {
        "message": f"Audio file '{file.filename}' uploaded successfully. Pipeline started in background.",
        "file_location": file_location,
        "pipeline_status": "started",
        "quarter_id": quarter_id
    } 