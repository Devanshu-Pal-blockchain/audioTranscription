from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging
import base64

from ..models.meeting_session import (
    SessionCreateRequest, 
    ChunkProcessRequest, 
    SessionEndRequest,
    UploadRequest,
    FinalSubmitRequest
)
from ..service.session_management_service import SessionManagementService
from ..service.auth_service import get_current_user
from ..service.db import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["Session Management"])

@router.post("/start")
async def start_recording_session(
    request: SessionCreateRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Start a new recording session for a meeting"""
    try:
        service = SessionManagementService(db)
        result = await service.start_new_session(request.meeting_id)
        
        logger.info(f"Session started by user {current_user['employee_id']}: {result['session_id']}")
        return {
            "success": True,
            "data": result,
            "message": "Recording session started successfully"
        }
    except Exception as e:
        logger.error(f"Error starting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-chunk")
async def process_audio_chunk(
    request: ChunkProcessRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Process an audio chunk when user pauses recording"""
    try:
        service = SessionManagementService(db)
        
        # Decode audio data from base64 if needed
        if request.chunk_data.startswith('data:'):
            # Handle data URL format
            header, data = request.chunk_data.split(',', 1)
            audio_bytes = base64.b64decode(data)
        else:
            # Handle direct base64
            audio_bytes = base64.b64decode(request.chunk_data)
        
        result = await service.process_audio_chunk(
            session_id=request.session_id,
            audio_data=audio_bytes,
            chunk_duration=request.duration_seconds
        )
        
        logger.info(f"Chunk processed for session {request.session_id}: {result['chunk_id']}")
        return {
            "success": True,
            "data": result,
            "message": "Audio chunk processed successfully"
        }
    except Exception as e:
        logger.error(f"Error processing chunk: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/end")
async def end_recording_session(
    request: SessionEndRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """End a recording session"""
    try:
        service = SessionManagementService(db)
        
        # Process final chunk if provided
        final_audio_bytes = None
        if request.final_chunk_data:
            if request.final_chunk_data.startswith('data:'):
                header, data = request.final_chunk_data.split(',', 1)
                final_audio_bytes = base64.b64decode(data)
            else:
                final_audio_bytes = base64.b64decode(request.final_chunk_data)
        
        result = await service.end_session(
            session_id=request.session_id,
            final_audio_data=final_audio_bytes
        )
        
        logger.info(f"Session ended: {request.session_id}")
        return {
            "success": True,
            "data": result,
            "message": "Recording session ended successfully"
        }
    except Exception as e:
        logger.error(f"Error ending session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/single-recording")
async def handle_single_recording(
    meeting_id: UUID = Form(...),
    audio_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Handle a single audio recording without pauses"""
    try:
        service = SessionManagementService(db)
        
        # Read audio file
        audio_data = await audio_file.read()
        
        # Get duration (this would need proper audio analysis)
        duration = 0.0  # TODO: Calculate actual duration
        
        result = await service.handle_single_recording(
            meeting_id=meeting_id,
            audio_data=audio_data,
            duration=duration
        )
        
        logger.info(f"Single recording processed for meeting {meeting_id}")
        return {
            "success": True,
            "data": result,
            "message": "Single recording processed successfully"
        }
    except Exception as e:
        logger.error(f"Error processing single recording: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-files")
async def upload_multiple_files(
    meeting_id: UUID = Form(...),
    upload_type: str = Form(...),  # "audio" or "transcript"
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Upload multiple audio or transcript files"""
    try:
        service = SessionManagementService(db)
        
        # Validate upload type
        if upload_type not in ["audio", "transcript"]:
            raise HTTPException(status_code=400, detail="Upload type must be 'audio' or 'transcript'")
        
        # Process files
        file_data = []
        for file in files:
            content = await file.read()
            file_data.append({
                "filename": file.filename,
                "content": content
            })
        
        result = await service.upload_multiple_files(
            meeting_id=meeting_id,
            files=file_data,
            upload_type=upload_type
        )
        
        logger.info(f"Uploaded {len(files)} {upload_type} files for meeting {meeting_id}")
        return {
            "success": True,
            "data": result,
            "message": f"Successfully uploaded {len(files)} {upload_type} files"
        }
    except Exception as e:
        logger.error(f"Error uploading files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/day-sessions/{meeting_id}")
async def get_meeting_day_sessions(
    meeting_id: UUID,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get all sessions and uploads for a meeting day"""
    try:
        service = SessionManagementService(db)
        result = await service.get_day_sessions(meeting_id)
        
        return {
            "success": True,
            "data": result,
            "message": "Meeting day sessions retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting day sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/finalize")
async def finalize_meeting_processing(
    request: FinalSubmitRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Finalize meeting processing with selected sessions and uploads"""
    try:
        service = SessionManagementService(db)
        result = await service.finalize_meeting_processing(
            meeting_id=request.meeting_id,
            selected_sessions=request.selected_sessions,
            selected_uploads=[str(uid) for uid in request.selected_uploads]
        )
        
        logger.info(f"Meeting {request.meeting_id} finalized with {len(request.selected_sessions)} sessions")
        return {
            "success": True,
            "data": result,
            "message": "Meeting processing finalized successfully"
        }
    except Exception as e:
        logger.error(f"Error finalizing meeting: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/pause")
async def pause_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Pause a recording session"""
    try:
        service = SessionManagementService(db)
        
        # Update session status to paused
        await service.collection.update_one(
            {"session_id": session_id},
            {"$set": {"status": "paused", "updated_at": "datetime.utcnow()"}}
        )
        
        return {
            "success": True,
            "message": f"Session {session_id} paused"
        }
    except Exception as e:
        logger.error(f"Error pausing session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/resume")
async def resume_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Resume a paused recording session"""
    try:
        service = SessionManagementService(db)
        
        # Update session status to active
        await service.collection.update_one(
            {"session_id": session_id},
            {"$set": {"status": "active", "updated_at": "datetime.utcnow()"}}
        )
        
        return {
            "success": True,
            "message": f"Session {session_id} resumed"
        }
    except Exception as e:
        logger.error(f"Error resuming session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sessions/{session_id}/status")
async def get_session_status(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get current status of a recording session"""
    try:
        service = SessionManagementService(db)
        session = await service.collection.find_one({"session_id": session_id})
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get chunk count
        chunk_count = await service.chunks_collection.count_documents({"session_id": session_id})
        
        return {
            "success": True,
            "data": {
                "session_id": session_id,
                "status": session["status"],
                "total_chunks": chunk_count,
                "created_at": session["created_at"],
                "last_activity": session.get("last_activity_at", session["created_at"])
            }
        }
    except Exception as e:
        logger.error(f"Error getting session status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Delete a recording session and all its chunks"""
    try:
        service = SessionManagementService(db)
        
        # Delete all chunks for this session
        await service.chunks_collection.delete_many({"session_id": session_id})
        
        # Delete the session
        result = await service.collection.delete_one({"session_id": session_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"Deleted session {session_id}")
        return {
            "success": True,
            "message": f"Session {session_id} deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sessions/{session_id}/select")
async def toggle_session_selection(
    session_id: str,
    selected: bool = Form(...),
    notes: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Toggle session selection for final processing"""
    try:
        service = SessionManagementService(db)
        
        update_data = {
            "selected_for_processing": selected,
            "updated_at": "datetime.utcnow()"
        }
        
        if notes:
            update_data["user_notes"] = notes
        
        result = await service.collection.update_one(
            {"session_id": session_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "success": True,
            "message": f"Session {session_id} {'selected' if selected else 'deselected'} for processing"
        }
    except Exception as e:
        logger.error(f"Error updating session selection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
