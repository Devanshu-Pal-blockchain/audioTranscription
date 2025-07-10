from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, date
import asyncio
import os
import tempfile
import json
import logging
from pathlib import Path

from ..models.meeting_session import MeetingSession, AudioChunk, MeetingUpload
from ..models.meeting import Meeting
from .base_service import BaseService

logger = logging.getLogger(__name__)

class SessionManagementService(BaseService):
    """Service for managing audio recording sessions with pause/resume functionality"""
    
    def __init__(self, db):
        super().__init__(db)
        self.collection = db.meeting_sessions
        self.chunks_collection = db.audio_chunks
        self.uploads_collection = db.meeting_uploads
        self.temp_dir = tempfile.gettempdir()
        
        # Ensure temp directories exist
        self.session_temp_dir = Path(self.temp_dir) / "vto_sessions"
        self.chunks_temp_dir = Path(self.temp_dir) / "vto_chunks"
        self.session_temp_dir.mkdir(exist_ok=True)
        self.chunks_temp_dir.mkdir(exist_ok=True)

    async def start_new_session(self, meeting_id: UUID) -> Dict[str, Any]:
        """Start a new recording session for a meeting day"""
        try:
            # Get meeting info
            meeting = await self.db.meetings.find_one({"meeting_id": meeting_id})
            if not meeting:
                raise ValueError(f"Meeting {meeting_id} not found")
            
            # Generate incremental session ID for the day
            meeting_day_id = f"meeting_{meeting_id}_{date.today().strftime('%Y%m%d')}"
            existing_sessions = await self.collection.count_documents({
                "meeting_day_id": meeting_day_id
            })
            
            session_number = existing_sessions + 1
            session_id = f"session_{session_number:03d}"
            
            # Create new session
            session = MeetingSession(
                session_id=session_id,
                meeting_id=meeting_id,
                session_start=datetime.utcnow(),
                meeting_day_id=meeting_day_id,
                session_number=session_number
            )
            
            result = await self.collection.insert_one(session.model_dump())
            
            logger.info(f"Started new session {session_id} for meeting {meeting_id}")
            
            return {
                "session_id": session_id,
                "meeting_day_id": meeting_day_id,
                "session_number": session_number,
                "status": "active",
                "message": f"Session {session_id} started successfully"
            }
            
        except Exception as e:
            logger.error(f"Error starting session: {str(e)}")
            raise

    async def process_audio_chunk(self, session_id: str, audio_data: bytes, chunk_duration: float) -> Dict[str, Any]:
        """Process an audio chunk when user pauses recording"""
        try:
            # Get session info
            session_doc = await self.collection.find_one({"session_id": session_id})
            if not session_doc:
                raise ValueError(f"Session {session_id} not found")
                
            session = MeetingSession(**session_doc)
            
            # Generate chunk ID
            chunk_sequence = session.current_chunk_sequence + 1
            chunk_id = f"{session_id}_chunk_{chunk_sequence:03d}"
            
            # Create audio chunk record
            chunk = AudioChunk(
                chunk_id=chunk_id,
                session_id=session_id,
                sequence_number=chunk_sequence,
                audio_duration=chunk_duration
            )
            
            # Save audio to temp file
            temp_audio_path = self.chunks_temp_dir / f"{chunk_id}.wav"
            with open(temp_audio_path, "wb") as f:
                f.write(audio_data)
            
            chunk.temp_audio_path = str(temp_audio_path)
            
            # Mark processing started
            chunk.mark_processing_started()
            
            # Save chunk to database
            await self.chunks_collection.insert_one(chunk.model_dump())
            
            # Process through transcription pipeline (async)
            transcript_result = await self._process_chunk_through_pipeline(chunk)
            
            # Get previous transcript if this isn't the first chunk
            previous_transcript = ""
            if chunk_sequence > 1:
                previous_transcript = await self._get_session_combined_transcript(session_id)
            
            # Combine with previous transcript
            combined_transcript = self._combine_transcripts(previous_transcript, transcript_result["transcript"])
            combined_summary = self._combine_summaries(previous_transcript, transcript_result["summary"])
            
            # Mark chunk as completed
            chunk.mark_processing_completed(
                transcript=combined_transcript,
                summary=combined_summary
            )
            
            # Update chunk in database
            await self.chunks_collection.update_one(
                {"chunk_id": chunk_id},
                {"$set": chunk.model_dump()}
            )
            
            # Update session with new chunk
            session.add_audio_chunk(chunk_id)
            await self.collection.update_one(
                {"session_id": session_id},
                {"$set": session.model_dump()}
            )
            
            logger.info(f"Processed chunk {chunk_id} for session {session_id}")
            
            return {
                "chunk_id": chunk_id,
                "transcript_id": chunk_id,  # Use chunk_id as transcript ID
                "transcript": combined_transcript,
                "summary": combined_summary,
                "status": "completed",
                "sequence_number": chunk_sequence
            }
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {str(e)}")
            # Mark chunk as failed if it was created
            if 'chunk' in locals():
                chunk.mark_processing_failed(str(e))
                await self.chunks_collection.update_one(
                    {"chunk_id": chunk.chunk_id},
                    {"$set": chunk.model_dump()}
                )
            raise

    async def end_session(self, session_id: str, final_audio_data: Optional[bytes] = None) -> Dict[str, Any]:
        """End a recording session and create final combined transcript"""
        try:
            # Process final chunk if provided
            if final_audio_data:
                await self.process_audio_chunk(session_id, final_audio_data, 0.0)
            
            # Get session
            session_doc = await self.collection.find_one({"session_id": session_id})
            if not session_doc:
                raise ValueError(f"Session {session_id} not found")
                
            session = MeetingSession(**session_doc)
            
            # Get all chunks for this session
            chunks_cursor = self.chunks_collection.find({"session_id": session_id}).sort("sequence_number", 1)
            chunks = await chunks_cursor.to_list(length=None)
            
            if not chunks:
                # No chunks - handle as single recording
                session.set_final_transcript("", session_id, "No content recorded")
            else:
                # Combine all chunk transcripts
                final_transcript = ""
                final_summary = ""
                
                for chunk_doc in chunks:
                    chunk = AudioChunk(**chunk_doc)
                    if chunk.raw_transcript:
                        final_transcript = chunk.raw_transcript  # Last chunk has all combined
                        final_summary = chunk.summary
                
                session.set_final_transcript(final_transcript, session_id, final_summary)
            
            # Mark session as completed
            session.end_session()
            
            # Update session in database
            await self.collection.update_one(
                {"session_id": session_id},
                {"$set": session.model_dump()}
            )
            
            logger.info(f"Ended session {session_id}")
            
            return {
                "session_id": session_id,
                "status": "completed",
                "final_transcript_id": session.final_transcript_file_id,
                "summary": session.summary,
                "total_chunks": session.total_chunks,
                "message": f"Session {session_id} completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            raise

    async def handle_single_recording(self, meeting_id: UUID, audio_data: bytes, duration: float) -> Dict[str, Any]:
        """Handle a single recording without pauses"""
        try:
            # Start session
            session_result = await self.start_new_session(meeting_id)
            session_id = session_result["session_id"]
            
            # Process as single chunk
            chunk_result = await self.process_audio_chunk(session_id, audio_data, duration)
            
            # End session immediately
            end_result = await self.end_session(session_id)
            
            return {
                "session_id": session_id,
                "transcript_id": chunk_result["transcript_id"],
                "transcript": chunk_result["transcript"],
                "summary": chunk_result["summary"],
                "status": "completed",
                "processing_type": "single_recording"
            }
            
        except Exception as e:
            logger.error(f"Error handling single recording: {str(e)}")
            raise

    async def upload_multiple_files(self, meeting_id: UUID, files: List[Dict], upload_type: str) -> List[Dict[str, Any]]:
        """Handle multiple file uploads (audio or transcript)"""
        try:
            results = []
            
            for i, file_data in enumerate(files):
                upload_id = f"upload_{upload_type}_{i+1:03d}"
                
                upload = MeetingUpload(
                    upload_id=UUID(),
                    meeting_id=meeting_id,
                    upload_type=upload_type,
                    original_filename=file_data.get("filename", f"{upload_type}_{i+1}"),
                    file_size_bytes=len(file_data["content"])
                )
                
                # Save file to temp location
                temp_path = self.session_temp_dir / f"{upload_id}_{upload.original_filename}"
                with open(temp_path, "wb") as f:
                    f.write(file_data["content"])
                
                upload.temp_file_path = str(temp_path)
                
                # Process based on type
                if upload_type == "audio":
                    # Process through transcription pipeline
                    result = await self._process_audio_upload(upload)
                else:  # transcript
                    # Process transcript file
                    result = await self._process_transcript_upload(upload)
                
                upload.processed_transcript = result["transcript_data"]
                upload.upload_summary = result["summary"]
                upload.processing_status = "completed"
                
                # Save upload record
                await self.uploads_collection.insert_one(upload.model_dump())
                
                results.append({
                    "upload_id": str(upload.upload_id),
                    "filename": upload.original_filename,
                    "summary": upload.upload_summary,
                    "status": "completed"
                })
            
            logger.info(f"Processed {len(files)} {upload_type} uploads for meeting {meeting_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error uploading files: {str(e)}")
            raise

    async def get_day_sessions(self, meeting_id: UUID) -> Dict[str, Any]:
        """Get all sessions for a meeting day"""
        try:
            meeting_day_id = f"meeting_{meeting_id}_{date.today().strftime('%Y%m%d')}"
            
            # Get all sessions
            sessions_cursor = self.collection.find({"meeting_day_id": meeting_day_id}).sort("session_number", 1)
            sessions = await sessions_cursor.to_list(length=None)
            
            # Get all uploads
            uploads_cursor = self.uploads_collection.find({"meeting_id": meeting_id})
            uploads = await uploads_cursor.to_list(length=None)
            
            session_summaries = []
            for session_doc in sessions:
                session = MeetingSession(**session_doc)
                session_summaries.append({
                    "session_id": session.session_id,
                    "session_number": session.session_number,
                    "status": session.status,
                    "summary": session.summary or "Session in progress...",
                    "total_chunks": session.total_chunks,
                    "duration": session.get_session_duration(),
                    "selected": session.selected_for_processing
                })
            
            upload_summaries = []
            for upload_doc in uploads:
                upload = MeetingUpload(**upload_doc)
                upload_summaries.append({
                    "upload_id": str(upload.upload_id),
                    "filename": upload.original_filename,
                    "type": upload.upload_type,
                    "summary": upload.upload_summary or "Processing...",
                    "selected": upload.is_selected
                })
            
            return {
                "meeting_day_id": meeting_day_id,
                "sessions": session_summaries,
                "uploads": upload_summaries,
                "total_sessions": len(sessions),
                "total_uploads": len(uploads)
            }
            
        except Exception as e:
            logger.error(f"Error getting day sessions: {str(e)}")
            raise

    async def finalize_meeting_processing(self, meeting_id: UUID, selected_sessions: List[str], selected_uploads: List[str]) -> Dict[str, Any]:
        """Process selected sessions and uploads into final meeting data"""
        try:
            # Get selected sessions
            sessions_cursor = self.collection.find({"session_id": {"$in": selected_sessions}})
            sessions = await sessions_cursor.to_list(length=None)
            
            # Get selected uploads
            uploads_cursor = self.uploads_collection.find({"upload_id": {"$in": [UUID(uid) for uid in selected_uploads]}})
            uploads = await uploads_cursor.to_list(length=None)
            
            # Combine all transcripts
            combined_transcript = ""
            combined_summaries = []
            
            # Add session transcripts
            for session_doc in sessions:
                session = MeetingSession(**session_doc)
                if session.final_transcript:
                    combined_transcript += f"\n\n=== {session.session_id} ===\n"
                    combined_transcript += session.final_transcript
                    if session.summary:
                        combined_summaries.append(f"{session.session_id}: {session.summary}")
            
            # Add upload transcripts
            for upload_doc in uploads:
                upload = MeetingUpload(**upload_doc)
                if upload.processed_transcript:
                    combined_transcript += f"\n\n=== {upload.original_filename} ===\n"
                    combined_transcript += upload.processed_transcript.get("text", "")
                    if upload.upload_summary:
                        combined_summaries.append(f"{upload.original_filename}: {upload.upload_summary}")
            
            # Process combined transcript through final VTO pipeline
            final_result = await self._process_final_vto_transcript(meeting_id, combined_transcript, combined_summaries)
            
            logger.info(f"Finalized meeting {meeting_id} processing with {len(selected_sessions)} sessions and {len(selected_uploads)} uploads")
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error finalizing meeting processing: {str(e)}")
            raise

    # Private helper methods
    
    async def _process_chunk_through_pipeline(self, chunk: AudioChunk) -> Dict[str, Any]:
        """Process audio chunk through transcription pipeline"""
        # TODO: Integrate with existing transcription pipeline
        # This should call the same pipeline used for regular audio processing
        # For now, returning mock data
        return {
            "transcript": f"Transcribed content for {chunk.chunk_id}",
            "summary": f"Summary for {chunk.chunk_id}",
            "issues": [],
            "solutions": [],
            "quality_score": 0.85
        }
    
    def _combine_transcripts(self, previous: str, new: str) -> str:
        """Combine previous transcript with new chunk transcript"""
        if not previous:
            return new
        return previous + "\n\n" + new
    
    def _combine_summaries(self, previous_transcript: str, new_summary: str) -> str:
        """Combine summaries from multiple chunks"""
        # Extract summary from previous transcript or create new combined summary
        if not previous_transcript:
            return new_summary
        return f"Combined session summary including: {new_summary}"
    
    async def _get_session_combined_transcript(self, session_id: str) -> str:
        """Get the current combined transcript for a session"""
        chunks_cursor = self.chunks_collection.find({"session_id": session_id}).sort("sequence_number", -1).limit(1)
        chunks = await chunks_cursor.to_list(length=1)
        
        if chunks and chunks[0].get("raw_transcript"):
            return chunks[0]["raw_transcript"]
        return ""
    
    async def _process_audio_upload(self, upload: MeetingUpload) -> Dict[str, Any]:
        """Process uploaded audio file"""
        # TODO: Integrate with existing audio processing pipeline
        return {
            "transcript_data": {"text": f"Transcript from {upload.original_filename}"},
            "summary": f"Summary of {upload.original_filename}"
        }
    
    async def _process_transcript_upload(self, upload: MeetingUpload) -> Dict[str, Any]:
        """Process uploaded transcript file"""
        # Read and validate transcript file
        with open(upload.temp_file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if transcript has timestamps
        has_timestamps = self._check_transcript_timestamps(content)
        
        return {
            "transcript_data": {
                "text": content,
                "has_timestamps": has_timestamps
            },
            "summary": f"Uploaded transcript: {upload.original_filename}"
        }
    
    def _check_transcript_timestamps(self, transcript: str) -> bool:
        """Check if transcript contains timestamp markers"""
        # Simple check for common timestamp formats
        import re
        timestamp_patterns = [
            r'\d{1,2}:\d{2}:\d{2}',  # HH:MM:SS
            r'\[\d{1,2}:\d{2}:\d{2}\]',  # [HH:MM:SS]
            r'\d{1,2}:\d{2}',  # MM:SS
        ]
        
        for pattern in timestamp_patterns:
            if re.search(pattern, transcript):
                return True
        return False
    
    async def _process_final_vto_transcript(self, meeting_id: UUID, combined_transcript: str, summaries: List[str]) -> Dict[str, Any]:
        """Process final combined transcript through VTO pipeline"""
        # TODO: Integrate with existing VTO processing pipeline
        # This should extract issues, solutions, rocks, todos, etc.
        return {
            "meeting_id": str(meeting_id),
            "final_transcript": combined_transcript,
            "processing_status": "completed",
            "extracted_data": {
                "issues": [],
                "solutions": [],
                "rocks": [],
                "todos": [],
                "summaries": summaries
            }
        }
