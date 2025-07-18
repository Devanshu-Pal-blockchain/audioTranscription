from jose import jwt, JWTError
from service.user_service import UserService

import os
import logging
import asyncio
import tempfile
import json
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from dotenv import load_dotenv
from models.user import User
from service.auth_service import facilitator_required
from service.script_pipeline_service import run_pipeline_for_audio, PipelineService, run_pipeline_for_transcript
from service.data_parser_service import parse_pipeline_response_to_files
from service.meeting_json_service import save_raw_context_json
from service.document_parser_service import parse_document_content

load_dotenv()

router = APIRouter()


# New endpoint: Upload transcript (raw context) JSON and save to DB only
@router.post("/upload-transcript")
async def upload_transcript(
    file: UploadFile = File(...),
    quarterWeeks: Optional[str] = Form(None),
    id: Optional[str] = Form(None),
    participants: Optional[str] = Form(None),
    current_user: User = Depends(facilitator_required)
):
    """
    Upload a transcript file (JSON, PDF, Word, Excel, or text), parse it, save to the raw context collection, and run the pipeline from step 2.
    Supports multiple file formats: .json, .pdf, .docx, .doc, .xlsx, .xls, .txt
    """
    import io
    import json

    # Read uploaded file content
    file_content = await file.read()
    
    try:
        # Parse the document content based on file type
        filename = file.filename or "unknown_file"
        file_type, parsed_content = parse_document_content(filename, file_content)
        logging.info(f"Successfully parsed {file_type} file: {filename}")
        
        # If it's not JSON, convert the parsed content to JSON format
        if file_type == 'json':
            transcript_json = parsed_content
        else:
            # For non-JSON files, the parsed_content is already in JSON format
            transcript_json = parsed_content
        
        # Debug logging - show structure being passed to pipeline
        logging.info(f"Parsed transcript structure: {type(transcript_json)}")
        logging.info(f"Transcript keys: {list(transcript_json.keys()) if isinstance(transcript_json, dict) else 'Not a dict'}")
        
        # Enhanced debug logging with word counts
        print(f"=== FRONTEND TRANSCRIPT DEBUG ===")
        print(f"File type: {file_type}")
        print(f"Filename: {filename}")
        print(f"Transcript data type: {type(transcript_json)}")
        
        if isinstance(transcript_json, dict):
            # Log first 200 characters of each text field for debugging
            for key in ['transcript', 'full_transcript', 'content', 'text']:
                if key in transcript_json:
                    content = str(transcript_json[key])
                    word_count = len(content.split())
                    char_count = len(content)
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"Found {key}: {word_count} words, {char_count} characters")
                    print(f"Preview: {content_preview}")
                    logging.info(f"Found {key}: {content_preview}")
        
        # Print entire structure (truncated)
        print(f"Full transcript structure: {str(transcript_json)[:500]}...")
        print(f"=== END FRONTEND TRANSCRIPT DEBUG ===")
        
    except ValueError as e:
        logging.error(f"Error parsing file {filename}: {e}")
        raise HTTPException(status_code=400, detail=f"Error parsing file: {e}")
    except Exception as e:
        logging.error(f"Unexpected error parsing file {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error parsing file: {e}")

    # Create a dummy file object for saving to raw context
    class DummyFile:
        def __init__(self, content):
            if isinstance(content, dict):
                # Convert dict to JSON bytes
                self.file = io.BytesIO(json.dumps(content).encode('utf-8'))
            else:
                self.file = io.BytesIO(content)
        def read(self):
            return self.file.read()
    
    # Save the parsed JSON content to raw context collection
    try:
        save_raw_context_json(DummyFile(transcript_json), str(current_user.employee_id))
        logging.info(f"Successfully saved parsed content from {filename} to raw context collection")
    except Exception as e:
        logging.error(f"Error saving to raw context collection: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving to database: {e}")

    # Require quarterWeeks and id (quarter_id)
    if quarterWeeks is None:
        raise HTTPException(status_code=400, detail="quarterWeeks is required from the frontend.")
    try:
        num_weeks = int(quarterWeeks)
    except Exception:
        raise HTTPException(status_code=400, detail="quarterWeeks must be an integer.")
    if id is None:
        raise HTTPException(status_code=400, detail="id (quarter_id) is required from the frontend.")
    quarter_id = id

    # Fetch participant details from the database using participant IDs
    participant_ids = []
    participant_info = []
    if participants:
        participant_ids = [pid.strip() for pid in participants.split(",") if pid.strip()]
        participant_details = await UserService.get_users_by_ids(participant_ids)
        found_ids = {str(user.employee_id) for user in participant_details}
        missing_ids = [pid for pid in participant_ids if pid not in found_ids]
        if missing_ids:
            logging.warning(f"Some participant IDs from the frontend were not found in the database: {missing_ids}")
        participant_info = [
            {
                "employee_id": str(user.employee_id),
                "employee_name": user.employee_name,
                "employee_responsibilities": user.employee_responsibilities,
                "employee_designation": user.employee_designation
            }
            for user in participant_details
        ]
        logging.info(f"Fetched participant info: {participant_info}")

    # Start pipeline in background (non-blocking)
    async def process_transcript_background(current_user):
        try:
            result = await run_pipeline_for_transcript(
                transcript_json,
                num_weeks=num_weeks,
                quarter_id=quarter_id,
                participants=participant_info,
                facilitator_id=str(current_user.employee_id)
            )
            if "error" in result:
                print(f"Pipeline (from transcript) failed: {result['error']}")
            else:
                print("Pipeline (from transcript) completed successfully!")
        except Exception as e:
            print(f"Background pipeline (from transcript) error: {e}")
    asyncio.create_task(process_transcript_background(current_user))

    return {
        "message": f"Transcript file '{file.filename}' uploaded, saved to raw context collection, and pipeline started.",
        "participants": participant_info
    }

from fastapi import Form

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Dependency to check facilitator role
async def facilitator_required_local(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = payload.get("role")
        if role != "facilitator":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Facilitators only.")
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")


# Set up logging (only once, at the top of the file)
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    current_user: User = Depends(facilitator_required)
):
    """
    Upload and process audio file to generate rocks and tasks
    
    Args:
        file: Audio file to process
        quarter_id: Optional quarter ID to associate rocks with
        current_user: Current authenticated facilitator user
        
    Returns:
        Dict with upload status and pipeline information
    """
    # Validate file extension
    allowed_exts = [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".webm", ".mp4"]
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
    
    # Require quarterWeeks from the frontend and convert to int
    if quarterWeeks is None:
        raise HTTPException(status_code=400, detail="quarterWeeks is required from the frontend.")
    try:
        num_weeks = int(quarterWeeks)
    except Exception:
        raise HTTPException(status_code=400, detail="quarterWeeks must be an integer.")
    
    # Require id from the frontend to use as quarter_id
    if id is None:
        raise HTTPException(status_code=400, detail="id (quarter_id) is required from the frontend.")
    quarter_id = id
    
    # Fetch participant details from the database using participant IDs
    participant_ids = []
    participant_info = []
    if participants:
        participant_ids = [pid.strip() for pid in participants.split(",") if pid.strip()]
        participant_details = await UserService.get_users_by_ids(participant_ids)
        found_ids = {str(user.employee_id) for user in participant_details}
        missing_ids = [pid for pid in participant_ids if pid not in found_ids]
        if missing_ids:
            logger.warning(f"Some participant IDs from the frontend were not found in the database: {missing_ids}")
        participant_info = [
            {
                "employee_id": str(user.employee_id),
                "employee_name": user.employee_name,
                "employee_responsibilities": user.employee_responsibilities,
                "employee_designation": user.employee_designation
            }
            for user in participant_details
        ]
        logger.info(f"Fetched participant info: {participant_info}")
    
    # Start pipeline in background (non-blocking)
    async def process_audio_background(current_user):
        try:
            # Run pipeline with the number of weeks and quarter_id from the frontend, and pass participant_info
            result = await run_pipeline_for_audio(
                file_location, 
                num_weeks=num_weeks, 
                quarter_id=quarter_id,
                participants=participant_info,
                facilitator_id=str(current_user['sub'])
            )
            
            if "error" in result:
                print(f"Pipeline failed: {result['error']}")
            else:
                print("Pipeline completed successfully!")
                
        except Exception as e:
            print(f"Background pipeline error: {e}")
        finally:
            # Clean up audio file
            try:
                os.remove(file_location)
            except:
                pass
    asyncio.create_task(process_audio_background(current_user))
    
    return {
        "message": f"Audio file '{file.filename}' uploaded successfully.",
        "participants": participant_info
    } 