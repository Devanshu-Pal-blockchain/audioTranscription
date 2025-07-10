from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime

class MeetingTimeline(BaseModel):
    """Timeline context for meetings"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True
    )
    
    year: int = Field(gt=1900, lt=10000, description="Year of the meeting")
    quarter: Optional[int] = Field(default=None, ge=1, le=4, description="Quarter number (1-4), required for quarterly/weekly meetings")
    week: Optional[int] = Field(default=None, ge=1, le=53, description="Week number in year, required for weekly meetings")
    meeting_number: int = Field(ge=1, description="Sequence number of meeting in the period")

class Meeting(BaseModel):
    """Enhanced meeting model for VTO implementation"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "meeting_id": "123e4567-e89b-12d3-a456-426614174000",
                "meeting_type": "quarterly",
                "meeting_title": "Q1 2024 Strategic Planning",
                "timeline": {
                    "year": 2024,
                    "quarter": 1,
                    "meeting_number": 1
                },
                "participants": ["123e4567-e89b-12d3-a456-426614174001"],
                "duration_minutes": 120,
                "status": "draft"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    meeting_id: UUID = Field(default_factory=uuid4)
    meeting_type: Literal["yearly", "quarterly", "weekly"] = Field(description="Type of meeting in VTO system")
    meeting_title: str = Field(min_length=1, description="Title of the meeting")
    timeline: MeetingTimeline = Field(description="Timeline context for the meeting")
    participants: List[UUID] = Field(default_factory=list, description="List of participant UUIDs")
    duration_minutes: Optional[int] = Field(default=None, ge=1, description="Meeting duration in minutes")
    status: Literal["draft", "in_progress", "completed", "cancelled"] = Field(default="draft", description="Meeting status")
    
    # File paths for audio and transcript
    audio_file_path: Optional[str] = Field(default=None, description="Path to uploaded audio file")
    transcript_file_path: Optional[str] = Field(default=None, description="Path to uploaded transcript file")
    
    # Meeting metadata
    organizer_id: UUID = Field(description="ID of the meeting organizer")
    location: Optional[str] = Field(default=None, description="Meeting location or platform")
    agenda: Optional[str] = Field(default=None, description="Meeting agenda")
    
    # Timestamps
    scheduled_start: Optional[datetime] = Field(default=None, description="Scheduled start time")
    actual_start: Optional[datetime] = Field(default=None, description="Actual start time")
    actual_end: Optional[datetime] = Field(default=None, description="Actual end time")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

    def get_meeting_context(self) -> str:
        """Generate context string for the meeting"""
        context_parts = [f"{self.meeting_type.title()} Meeting"]
        
        if self.meeting_type == "yearly":
            context_parts.append(f"Year {self.timeline.year}")
        elif self.meeting_type == "quarterly":
            context_parts.append(f"Q{self.timeline.quarter} {self.timeline.year}")
        elif self.meeting_type == "weekly":
            context_parts.append(f"Week {self.timeline.week}, Q{self.timeline.quarter} {self.timeline.year}")
            
        context_parts.append(f"#{self.timeline.meeting_number}")
        return " - ".join(context_parts)
