"""
Recording Routes - Handle session-based audio recording with pause/resume functionality
"""
from jose import jwt, JWTError
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordBearer
from typing import Optional, Dict, Any, List
import os
import json
import asyncio
import tempfile
import logging
from datetime import datetime

from models.user import User
from service.auth_service import admin_required
from service.script_pipeline_service import PipelineService
from utils.id_generator import generate_random_id, generate_session_id, generate_chunk_id
from service.meeting_json_service import save_raw_context_json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for active recording sessions and completed sessions
# In production, this should be stored in Redis or database
active_recording_sessions: Dict[str, Dict[str, Any]] = {}
completed_sessions: Dict[str, Dict[str, Any]] = {}

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

@router.post("/start-session")
async def start_recording_session(
    quarter_id: str = Form(...),
    participants: Optional[str] = Form(None),
    quarterWeeks: Optional[str] = Form(None),
    meetingTitle: Optional[str] = Form(None),
    meetingDescription: Optional[str] = Form(None),
    current_user: User = Depends(admin_required)
):
    """
    Start a new recording session and return session ID
    """
    session_id = generate_session_id()
    
    # Store session metadata
    active_recording_sessions[session_id] = {
        "session_id": session_id,
        "quarter_id": quarter_id,
        "participants": participants,
        "quarterWeeks": quarterWeeks,
        "meetingTitle": meetingTitle,
        "meetingDescription": meetingDescription,
        "admin_id": str(current_user.employee_id),
        "chunks": [],
        "current_transcript": "",
        "transcript_id": None,
        "created_at": datetime.utcnow().isoformat(),
        "status": "active",
        "is_paused": False,
        "chunk_counter": 0
    }
    
    logger.info(f"Started recording session: {session_id}")
    
    return {
        "session_id": session_id,
        "message": "Recording session started successfully"
    }

@router.post("/process-chunk")
async def process_audio_chunk(
    session_id: str = Form(...),
    is_pause_chunk: bool = Form(...),  # True if this chunk is sent on pause
    file: UploadFile = File(...),
    current_user: User = Depends(admin_required)
):
    """
    Process an audio chunk from recording session
    This is called when user pauses recording (is_pause_chunk=True) 
    or when user ends recording (is_pause_chunk=False)
    """
    
    # Validate session exists
    if session_id not in active_recording_sessions:
        raise HTTPException(status_code=404, detail="Recording session not found")
    
    session = active_recording_sessions[session_id]
    session["chunk_counter"] += 1
    chunk_number = session["chunk_counter"]
    
    logger.info(f"Processing chunk {chunk_number} for session {session_id}, is_pause_chunk: {is_pause_chunk}")
    
    # Validate file
    allowed_exts = [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".webm", ".mp4"]
    if not file.filename or not any(file.filename.endswith(ext) for ext in allowed_exts):
        raise HTTPException(status_code=400, detail="Only audio files are allowed.")
    
    # Generate chunk ID
    chunk_id = generate_chunk_id(session_id, chunk_number)
    
    # Ensure the chunks directory exists
    chunks_dir = os.path.abspath("uploaded_audios/chunks")
    os.makedirs(chunks_dir, exist_ok=True)
    
    # Save audio file temporarily with a more descriptive name
    file_extension = ".webm"  # Default extension
    if file.filename:
        if file.filename.endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.webm', '.mp4')):
            file_extension = os.path.splitext(file.filename)[1]
    
    file_location = os.path.join(chunks_dir, f"{session_id}_chunk_{chunk_number}{file_extension}")
    
    # Read file content and save
    file_content = await file.read()
    logger.info(f"Saving audio chunk to: {file_location}, size: {len(file_content)} bytes")
    
    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="Audio file is empty")
    
    with open(file_location, "wb") as f:
        f.write(file_content)
    
    # Verify file was saved
    if not os.path.exists(file_location):
        raise HTTPException(status_code=500, detail=f"Failed to save audio file to {file_location}")
    
    actual_file_size = os.path.getsize(file_location)
    logger.info(f"Audio file saved successfully: {file_location}, size: {actual_file_size} bytes")
    
    # Get or create transcript ID for this session
    if session["transcript_id"] is None:
        session["transcript_id"] = generate_random_id(10)
    
    transcript_id = session["transcript_id"]
    
    # Return immediately and process in background
    chunk_info = {
        "chunk_id": chunk_id,
        "chunk_number": chunk_number,
        "file_path": file_location,
        "transcript": "",  # Will be updated by background task
        "is_pause_chunk": is_pause_chunk,
        "processed_at": datetime.utcnow().isoformat(),
        "duration": 0,  # Will be updated by background task
        "status": "processing"
    }
    
    session["chunks"].append(chunk_info)
    session["is_paused"] = is_pause_chunk
    
    # Process transcription in background
    async def process_transcription_async():
        try:
            pipeline = PipelineService(admin_id=session["admin_id"])
            
            # Transcribe only (step 1 of pipeline)
            transcription = await pipeline.transcribe_audio(file_location)
            
            if transcription and "text" in transcription:
                chunk_transcript = transcription["text"].strip()
                logger.info(f"Transcription completed for chunk {chunk_id}: {len(chunk_transcript)} characters")
                
                # Update session transcript (amend with previous chunks)
                if session["current_transcript"]:
                    session["current_transcript"] += " " + chunk_transcript
                else:
                    session["current_transcript"] = chunk_transcript
                
                # Update chunk info
                for chunk in session["chunks"]:
                    if chunk["chunk_id"] == chunk_id:
                        chunk["transcript"] = chunk_transcript
                        chunk["duration"] = transcription.get("duration", 0)
                        chunk["status"] = "completed"
                        break
                
                logger.info(f"Background processing completed for chunk {chunk_id}")
            else:
                # Mark as failed
                for chunk in session["chunks"]:
                    if chunk["chunk_id"] == chunk_id:
                        chunk["status"] = "failed"
                        break
                logger.error(f"Background transcription failed for chunk {chunk_id}")
                
        except Exception as e:
            logger.error(f"Background processing error for chunk {chunk_id}: {e}")
            # Mark as failed
            for chunk in session["chunks"]:
                if chunk["chunk_id"] == chunk_id:
                    chunk["status"] = "failed"
                    break
            
            # Clean up file if transcription failed
            if os.path.exists(file_location):
                try:
                    os.remove(file_location)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up file {file_location}: {cleanup_error}")
    
    # Start background processing
    asyncio.create_task(process_transcription_async())
    
    logger.info(f"Processed chunk {chunk_id} for session {session_id} (pause: {is_pause_chunk}) - processing in background")
    
    return {
        "chunk_id": chunk_id,
        "transcript_id": transcript_id,
        "chunk_transcript": "",  # Will be available later
        "combined_transcript": session["current_transcript"],
        "total_chunks": len(session["chunks"]),
        "status": "processing",
        "message": f"Audio chunk {chunk_number} received and processing in background"
    }

@router.post("/end-session")
async def end_recording_session(
    session_id: str = Form(...),
    is_paused_flag: bool = Form(...),  # Flag indicating if recording was paused when ended
    current_user: User = Depends(admin_required)
):
    """
    End recording session
    If is_paused_flag is False, it means the last audio chunk hasn't been processed yet
    """
    
    # Validate session exists
    if session_id not in active_recording_sessions:
        raise HTTPException(status_code=404, detail="Recording session not found")
    
    session = active_recording_sessions[session_id]
    
    # Wait a moment for any pending transcriptions to complete if not paused
    if not is_paused_flag:
        # Give a longer grace period for the last chunk to be uploaded and processed
        logger.info(f"Session ending while recording - waiting for final chunk upload")
        await asyncio.sleep(2.0)
    
    # Build transcript from available chunks if current_transcript is empty
    if not session["current_transcript"]:
        # Try to build transcript from completed chunks
        completed_chunks = [chunk for chunk in session["chunks"] if chunk.get("transcript")]
        if completed_chunks:
            # Sort by chunk number and concatenate
            completed_chunks.sort(key=lambda x: x.get("chunk_number", 0))
            session["current_transcript"] = " ".join([chunk["transcript"] for chunk in completed_chunks])
            logger.info(f"Built transcript from {len(completed_chunks)} completed chunks")
        
        # If still no transcript and not paused (meaning we should have content), wait a bit more
        if not session["current_transcript"] and not is_paused_flag and session["chunks"]:
            logger.info(f"No transcript yet but session ended while recording - waiting for processing")
            await asyncio.sleep(1.0)
            
            # Try again to build transcript
            completed_chunks = [chunk for chunk in session["chunks"] if chunk.get("transcript")]
            if completed_chunks:
                completed_chunks.sort(key=lambda x: x.get("chunk_number", 0))
                session["current_transcript"] = " ".join([chunk["transcript"] for chunk in completed_chunks])
                logger.info(f"Built transcript from {len(completed_chunks)} completed chunks after waiting")
        
        # If still no transcript but we have chunks, provide clear status
        if not session["current_transcript"] and session["chunks"]:
            logger.warning(f"Ending session {session_id} with {len(session['chunks'])} chunks but no completed transcriptions yet")
            # Don't set a placeholder - let it remain empty if no actual transcript exists
            session["current_transcript"] = ""
    
    # Validate we have meaningful content before saving
    has_meaningful_content = (
        session["current_transcript"].strip() and 
        session["current_transcript"] != "[Transcription in progress - chunks uploaded but not yet processed]"
    )
    
    if not has_meaningful_content and not is_paused_flag:
        logger.error(f"Session {session_id} ended while recording but no transcript was generated")
        # Still save the session but mark it clearly
        session["current_transcript"] = ""
    
    try:
        # Prepare transcript JSON structure
        transcript_json = {
            "session_id": session_id,
            "transcript_id": session["transcript_id"],
            "transcript": session["current_transcript"],
            "chunks": session["chunks"],
            "metadata": {
                "quarter_id": session["quarter_id"],
                "meetingTitle": session.get("meetingTitle"),
                "meetingDescription": session.get("meetingDescription"),
                "total_chunks": len(session["chunks"]),
                "created_at": session["created_at"],
                "ended_at": datetime.utcnow().isoformat(),
                "is_paused_flag": is_paused_flag
            }
        }
        
        # Save raw transcript to temp storage (not main pipeline yet)
        # This follows the requirement that transcripts are raw until submit
        try:
            transcript_json_str = json.dumps(transcript_json, indent=2)
            temp_file_path = f"uploaded_audios/temp_transcripts/session_{session_id}.json"
            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
            
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                f.write(transcript_json_str)
            
            logger.info(f"Saved raw transcript to: {temp_file_path}")
        except Exception as save_error:
            logger.warning(f"Could not save transcript file: {save_error}")
            # Continue anyway, transcript is in memory
        
        # Mark session as completed and move to completed sessions
        session["status"] = "completed"
        session["ended_at"] = datetime.utcnow().isoformat()
        session["is_paused_flag"] = is_paused_flag
        
        # Move to completed sessions storage
        completed_sessions[session_id] = session.copy()
        
        response_data = {
            "session_id": session_id,
            "transcript_id": session["transcript_id"],
            "total_chunks": len(session["chunks"]),
            "final_transcript": session["current_transcript"],
            "message": "Recording session ended successfully. Raw transcript saved."
        }
        
        # Keep session in active until user submits (for potential additional sessions)
        # Don't delete from active_recording_sessions yet
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error ending recording session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to end recording session: {str(e)}")

@router.get("/sessions")
async def get_all_sessions(
    current_user: User = Depends(admin_required)
):
    """
    Get all active and completed sessions for the current user
    """
    user_sessions = {
        "active": [],
        "completed": []
    }
    
    # Filter sessions by admin_id
    for session_id, session in active_recording_sessions.items():
        if session["admin_id"] == str(current_user.employee_id):
            user_sessions["active"].append({
                "session_id": session_id,
                "transcript_id": session["transcript_id"],
                "status": session["status"],
                "total_chunks": len(session["chunks"]),
                "transcript_length": len(session["current_transcript"]),
                "created_at": session["created_at"],
                "meetingTitle": session.get("meetingTitle"),
                "is_paused": session.get("is_paused", False)
            })
    
    for session_id, session in completed_sessions.items():
        if session["admin_id"] == str(current_user.employee_id):
            user_sessions["completed"].append({
                "session_id": session_id,
                "transcript_id": session["transcript_id"],
                "status": session["status"],
                "total_chunks": len(session["chunks"]),
                "transcript_length": len(session["current_transcript"]),
                "created_at": session["created_at"],
                "ended_at": session.get("ended_at"),
                "meetingTitle": session.get("meetingTitle")
            })
    
    return user_sessions

@router.post("/submit-sessions")
async def submit_selected_sessions(
    session_ids: str = Form(...),  # Comma-separated session IDs
    quarter_id: str = Form(...),
    quarterWeeks: str = Form("12"),
    current_user: User = Depends(admin_required)
):
    """
    Submit selected recording sessions to the main pipeline
    This triggers the full processing pipeline for the selected sessions
    """
    
    try:
        # Parse session IDs
        selected_session_ids = [sid.strip() for sid in session_ids.split(",") if sid.strip()]
        
        if not selected_session_ids:
            raise HTTPException(status_code=400, detail="No sessions provided")
        
        # Collect all transcripts from selected sessions
        all_transcripts = []
        session_metadata = []
        
        for session_id in selected_session_ids:
            # Check in both active and completed sessions
            session = None
            if session_id in active_recording_sessions:
                session = active_recording_sessions[session_id]
            elif session_id in completed_sessions:
                session = completed_sessions[session_id]
            
            if not session:
                raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
            
            if session["admin_id"] != str(current_user.employee_id):
                raise HTTPException(status_code=403, detail=f"Access denied for session {session_id}")
            
            # Check if session has meaningful transcript content
            transcript_content = session["current_transcript"].strip()
            if not transcript_content:
                logger.warning(f"Skipping session {session_id} - no transcript content available")
                continue  # Skip sessions without transcripts to avoid unnecessary LLM costs
            
            # Check for minimal content that won't generate business insights
            word_count = len(transcript_content.split())
            if word_count < 10:  # Less than 10 words is likely just test content
                logger.warning(f"Skipping session {session_id} - transcript too short ({word_count} words): '{transcript_content[:100]}...'")
                continue
            
            # Collect transcript data
            transcript_data = {
                "session_id": session_id,
                "transcript_id": session["transcript_id"],
                "transcript": transcript_content,
                "full_transcript": transcript_content,  # Pipeline expects this field
                "chunks": session["chunks"],
                "metadata": {
                    "quarter_id": session["quarter_id"],
                    "meetingTitle": session.get("meetingTitle"),
                    "meetingDescription": session.get("meetingDescription"),
                    "total_chunks": len(session["chunks"]),
                    "created_at": session["created_at"],
                    "ended_at": session.get("ended_at", datetime.utcnow().isoformat())
                }
            }
            
            all_transcripts.append(transcript_data)
            session_metadata.append({
                "session_id": session_id,
                "transcript_id": session["transcript_id"],
                "total_chunks": len(session["chunks"])
            })
        
        # Check if we have any valid sessions to submit
        if not all_transcripts:
            logger.warning(f"No sessions with valid transcripts found from {len(selected_session_ids)} requested sessions")
            
            # Check if sessions exist but have insufficient content
            skipped_sessions = []
            for session_id in selected_session_ids:
                session = active_recording_sessions.get(session_id) or completed_sessions.get(session_id)
                if session:
                    transcript_content = session["current_transcript"].strip()
                    word_count = len(transcript_content.split()) if transcript_content else 0
                    skipped_sessions.append({
                        "session_id": session_id,
                        "reason": "no_content" if not transcript_content else f"insufficient_content ({word_count} words)",
                        "content_preview": transcript_content[:100] if transcript_content else "No content"
                    })
            
            if skipped_sessions:
                detail_msg = "Sessions were skipped due to insufficient business content. "
                detail_msg += "For ROCKs to be generated, recordings should contain business discussions, "
                detail_msg += "tasks, goals, or actionable items. Try recording actual meeting content instead of test phrases."
                
                raise HTTPException(
                    status_code=400, 
                    detail=detail_msg,
                    headers={"X-Skipped-Sessions": json.dumps(skipped_sessions)}
                )
            else:
                raise HTTPException(
                    status_code=400, 
                    detail=f"No sessions with valid transcripts found. Sessions may not have completed transcription yet."
                )
        
        # Get session parameters
        try:
            num_weeks = int(quarterWeeks)
        except:
            num_weeks = 12
        
        # Parse participants from first session (assuming same participants for all sessions)
        participant_info = []
        if all_transcripts and all_transcripts[0].get("metadata", {}).get("quarter_id"):
            first_session = None
            for session_id in selected_session_ids:
                if session_id in active_recording_sessions:
                    first_session = active_recording_sessions[session_id]
                    break
                elif session_id in completed_sessions:
                    first_session = completed_sessions[session_id]
                    break
            
            if first_session and first_session.get("participants"):
                from service.user_service import UserService
                participant_ids = [pid.strip() for pid in first_session["participants"].split(",") if pid.strip()]
                participant_details = await UserService.get_users_by_ids(participant_ids)
                participant_info = [
                    {
                        "employee_id": str(user.employee_id),
                        "employee_name": user.employee_name,
                        "employee_responsibilities": user.employee_responsibilities,
                        "employee_designation": user.employee_designation
                    }
                    for user in participant_details
                ]
        
        # Start full pipeline for all selected transcripts
        async def run_full_pipeline():
            try:
                from service.script_pipeline_service import run_pipeline_for_transcript
                
                # Process each transcript through the full pipeline
                for transcript_data in all_transcripts:
                    result = await run_pipeline_for_transcript(
                        transcript_data,
                        num_weeks=num_weeks,
                        quarter_id=quarter_id,
                        participants=participant_info,
                        admin_id=str(current_user.employee_id)
                    )
                    
                    if "error" in result:
                        logger.error(f"Pipeline failed for session {transcript_data['session_id']}: {result['error']}")
                    else:
                        logger.info(f"Pipeline completed successfully for session {transcript_data['session_id']}")
                        
            except Exception as e:
                logger.error(f"Background pipeline error for sessions {selected_session_ids}: {e}")
        
        # Start pipeline in background
        asyncio.create_task(run_full_pipeline())
        
        # Clean up sessions after successful submission
        async def cleanup_submitted_sessions():
            await asyncio.sleep(300)  # Wait 5 minutes before cleanup
            for session_id in selected_session_ids:
                # Clean up chunk files
                session = active_recording_sessions.get(session_id) or completed_sessions.get(session_id)
                if session:
                    for chunk in session["chunks"]:
                        try:
                            if os.path.exists(chunk["file_path"]):
                                os.remove(chunk["file_path"])
                        except Exception as e:
                            logger.warning(f"Failed to clean up chunk file {chunk['file_path']}: {e}")
                
                # Remove from memory
                if session_id in active_recording_sessions:
                    del active_recording_sessions[session_id]
                if session_id in completed_sessions:
                    del completed_sessions[session_id]
        
        asyncio.create_task(cleanup_submitted_sessions())
        
        return {
            "message": f"Successfully submitted {len(selected_session_ids)} sessions to pipeline",
            "submitted_sessions": session_metadata,
            "total_transcripts": len(all_transcripts),
            "participant_info": participant_info
        }
        
    except Exception as e:
        logger.error(f"Error submitting sessions {session_ids}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit sessions: {str(e)}")

@router.get("/session-status/{session_id}")
async def get_recording_session_status(
    session_id: str,
    current_user: User = Depends(admin_required)
):
    """
    Get status of a specific recording session with chunk processing status
    """
    # Check in both active and completed sessions
    session = None
    if session_id in active_recording_sessions:
        session = active_recording_sessions[session_id]
    elif session_id in completed_sessions:
        session = completed_sessions[session_id]
    
    if not session:
        raise HTTPException(status_code=404, detail="Recording session not found")
    
    if session["admin_id"] != str(current_user.employee_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Calculate processing statistics
    total_chunks = len(session["chunks"])
    completed_chunks = sum(1 for chunk in session["chunks"] if chunk.get("status") == "completed")
    processing_chunks = sum(1 for chunk in session["chunks"] if chunk.get("status") == "processing")
    failed_chunks = sum(1 for chunk in session["chunks"] if chunk.get("status") == "failed")
    
    return {
        "session_id": session_id,
        "status": session["status"],
        "transcript_id": session["transcript_id"],
        "total_chunks": total_chunks,
        "completed_chunks": completed_chunks,
        "processing_chunks": processing_chunks,
        "failed_chunks": failed_chunks,
        "current_transcript_length": len(session["current_transcript"]),
        "created_at": session["created_at"],
        "ended_at": session.get("ended_at"),
        "is_paused": session.get("is_paused", False),
        "last_chunk_at": session["chunks"][-1]["processed_at"] if session["chunks"] else None,
        "chunks": [
            {
                "id": chunk["chunk_id"], # Frontend expects 'id'
                "chunk_id": chunk["chunk_id"],
                "chunk_number": chunk["chunk_number"],
                "status": chunk.get("status", "unknown"),
                "is_pause_chunk": chunk["is_pause_chunk"],
                "transcript": chunk.get("transcript", ""), # Include full transcript
                "transcript_length": len(chunk.get("transcript", "")),
                "duration": chunk.get("duration", 0), # Include duration
                "processed_at": chunk["processed_at"]
            }
            for chunk in session["chunks"]
        ]
    }

@router.delete("/cancel-session/{session_id}")
async def cancel_recording_session(
    session_id: str,
    current_user: User = Depends(admin_required)
):
    """
    Cancel an active recording session
    """
    session = None
    session_location = None
    
    if session_id in active_recording_sessions:
        session = active_recording_sessions[session_id]
        session_location = "active"
    elif session_id in completed_sessions:
        session = completed_sessions[session_id]
        session_location = "completed"
    
    if not session:
        return {
            "message": f"Recording session {session_id} not found or already cancelled"
        }
    
    if session["admin_id"] != str(current_user.employee_id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Clean up any temporary files
    for chunk in session["chunks"]:
        try:
            if os.path.exists(chunk["file_path"]):
                os.remove(chunk["file_path"])
        except Exception as e:
            logger.warning(f"Failed to clean up chunk file {chunk['file_path']}: {e}")
    
    # Remove session from memory
    if session_location == "active":
        del active_recording_sessions[session_id]
    else:
        del completed_sessions[session_id]
    
    return {
        "message": f"Recording session {session_id} cancelled successfully"
    }
