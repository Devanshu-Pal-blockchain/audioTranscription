from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime, date

class Milestone(BaseModel):
    """Milestone model for tracking progress of rocks and to-dos"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "milestone_id": "123e4567-e89b-12d3-a456-426614174000",
                "parent_rock_id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "Complete infrastructure assessment",
                "description": "Evaluate current cloud infrastructure capacity and identify bottlenecks",
                "due_date": "2024-07-18",
                "week_number": 1,
                "status": "pending",
                "summary": "Initial assessment milestone to understand infrastructure requirements"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    milestone_id: UUID = Field(default_factory=uuid4)
    
    # Parent relationship - milestones only belong to rocks
    parent_rock_id: UUID = Field(description="ID of parent rock (milestones are only for rocks)")
    
    # Milestone content
    title: str = Field(min_length=1, description="Brief title describing the milestone")
    description: str = Field(min_length=1, description="Detailed description of what needs to be accomplished")
    
    # Timeline
    due_date: date = Field(description="Target completion date for the milestone")
    week_number: Optional[int] = Field(default=None, ge=1, le=12, description="Week number for quarterly milestones (default 12 weeks)")
    
    # Completion tracking - using status instead of check_completed
    status: Literal["pending", "in_progress", "completed"] = Field(
        default="pending", 
        description="Current status of the milestone"
    )
    
    # Content and context
    summary: str = Field(description="AI-generated summary of the milestone")
    
    # Assignment and responsibility
    assigned_to: Optional[str] = Field(default=None, description="Person assigned to this milestone")
    
    # Additional metadata
    dependencies: Optional[list[str]] = Field(default_factory=list, description="Dependencies for this milestone")
    deliverables: Optional[list[str]] = Field(default_factory=list, description="Expected deliverables")
    success_criteria: Optional[str] = Field(default=None, description="Criteria for completion")
    
    # Effort tracking
    estimated_hours: Optional[int] = Field(default=None, ge=0, description="Estimated effort in hours")
    actual_hours: Optional[int] = Field(default=None, ge=0, description="Actual time spent in hours")
    
    # Meeting context (if milestone was created from meeting)
    meeting_reference: Optional[UUID] = Field(default=None, description="Meeting where milestone was identified")
    timestamp: Optional[str] = Field(default=None, description="Timestamp in meeting when mentioned")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None, description="When work on milestone started")
    completed_at: Optional[datetime] = Field(default=None, description="When milestone was completed")

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

    def is_overdue(self) -> bool:
        """Check if milestone is overdue"""
        if self.status in ["completed", "cancelled"]:
            return False
        return date.today() > self.due_date

    def mark_completed(self) -> None:
        """Mark milestone as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def start_milestone(self) -> None:
        """Mark milestone as started"""
        self.status = "in_progress"
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def get_time_remaining(self) -> int:
        """Get days remaining until due date"""
        if self.status == "completed":
            return 0
        delta = self.due_date - date.today()
        return max(0, delta.days)

    def get_progress_status(self) -> str:
        """Get human-readable progress status"""
        if self.status == "completed":
            return "Completed"
        elif self.is_overdue():
            return "Overdue"
        elif self.get_time_remaining() <= 1:
            return "Due Soon"
        elif self.status == "in_progress":
            return "In Progress"
        else:
            return "Pending"
