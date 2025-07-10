from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime

class MeetingSession(BaseModel):
    """Meeting session model for handling pause/resume recording flow"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "session_id": 1,
                "meeting_id": "123e4567-e89b-12d3-a456-426614174000",
                "session_start": "2024-07-10T09:00:00Z",
                "session_end": "2024-07-10T12:00:00Z",
                "total_audio_chunks": 6,
                "session_summary": "Discussed Q3 objectives and resource allocation",
                "is_selected": True
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    session_id: int = Field(description="Incremental session ID for the day")
    meeting_id: UUID = Field(description="Reference to the parent meeting")
    
    # Session timing
    session_start: datetime = Field(description="When this session started")
    session_end: Optional[datetime] = Field(default=None, description="When this session ended")
    
    # Audio and transcript tracking
    audio_chunks: List["AudioChunk"] = Field(default_factory=list, description="All audio chunks for this session")
    total_audio_chunks: int = Field(default=0, description="Total number of audio chunks in this session")
    combined_transcript_id: Optional[int] = Field(default=None, description="ID of the combined transcript for this session")
    
    # Session content
    session_summary: Optional[str] = Field(default=None, description="Summary of what was discussed in this session")
    session_transcript: Optional[str] = Field(default=None, description="Combined transcript for the entire session")
    
    # Selection for final processing
    is_selected: bool = Field(default=True, description="Whether this session is selected for final processing")
    
    # Processing status
    processing_status: Literal["recording", "processing", "completed", "failed"] = Field(
        default="recording", 
        description="Current processing status"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

class AudioChunk(BaseModel):
    """Audio chunk model for handling paused segments"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True
    )

    id: UUID = Field(default_factory=uuid4)
    chunk_id: int = Field(description="Incremental chunk ID within session")
    session_id: int = Field(description="Parent session ID")
    meeting_id: UUID = Field(description="Reference to the parent meeting")
    
    # Audio metadata
    chunk_start_time: datetime = Field(description="When this chunk recording started")
    chunk_end_time: datetime = Field(description="When this chunk recording ended")
    duration_seconds: int = Field(ge=0, description="Duration of this audio chunk in seconds")
    
    # File references (temp storage paths, not saved in DB)
    temp_audio_path: Optional[str] = Field(default=None, description="Temporary storage path for audio file")
    
    # Transcript data
    transcript_data: Optional[Dict[str, Any]] = Field(default=None, description="Processed transcript data for this chunk")
    chunk_summary: Optional[str] = Field(default=None, description="Summary of this audio chunk content")
    
    # Processing status
    processing_status: Literal["pending", "processing", "completed", "failed"] = Field(
        default="pending", 
        description="Processing status of this chunk"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

class MeetingUpload(BaseModel):
    """Model for handling multiple file uploads per meeting"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True
    )

    id: UUID = Field(default_factory=uuid4)
    upload_id: UUID = Field(default_factory=uuid4)
    meeting_id: UUID = Field(description="Reference to the parent meeting")
    
    # Upload metadata
    upload_type: Literal["audio", "transcript"] = Field(description="Type of file being uploaded")
    original_filename: str = Field(description="Original name of the uploaded file")
    file_size_bytes: int = Field(ge=0, description="Size of the uploaded file in bytes")
    
    # Processing
    temp_file_path: Optional[str] = Field(default=None, description="Temporary storage path")
    processed_transcript: Optional[Dict[str, Any]] = Field(default=None, description="Processed transcript data")
    upload_summary: Optional[str] = Field(default=None, description="Summary of uploaded content")
    
    # Selection for final processing
    is_selected: bool = Field(default=True, description="Whether this upload is selected for final processing")
    
    # Processing status
    processing_status: Literal["uploaded", "processing", "completed", "failed"] = Field(
        default="uploaded", 
        description="Current processing status"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

# Request models for API endpoints

class SessionCreateRequest(BaseModel):
    """Request to start a new meeting session"""
    meeting_id: UUID

class ChunkProcessRequest(BaseModel):
    """Request to process an audio chunk during pause"""
    session_id: int
    chunk_data: str = Field(description="Base64 encoded audio data or file path")
    duration_seconds: int

class SessionEndRequest(BaseModel):
    """Request to end a recording session"""
    session_id: int
    final_chunk_data: Optional[str] = Field(default=None, description="Final audio chunk if any")

class UploadRequest(BaseModel):
    """Request for uploading files"""
    meeting_id: UUID
    upload_type: Literal["audio", "transcript"]
    files: List[str] = Field(description="List of file paths or base64 data")

class FinalSubmitRequest(BaseModel):
    """Request to finalize meeting with selected sessions/uploads"""
    meeting_id: UUID
    selected_sessions: List[int] = Field(default_factory=list, description="Selected session IDs")
    selected_uploads: List[UUID] = Field(default_factory=list, description="Selected upload IDs")
