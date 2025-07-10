from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime, date

class ToDo(BaseModel):
    """To-do model for tasks that can be completed within 1-2 weeks (parallel to rocks, not nested)"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "todo_id": "123e4567-e89b-12d3-a456-426614174000",
                "meeting_id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "Update security protocols",
                "description": "Review and update company security protocols based on new regulations",
                "parent_rock_id": "123e4567-e89b-12d3-a456-426614174002",
                "owner": "Jane Smith",
                "due_date": "2024-07-25",
                "status": "pending",
                "summary": "Quick security update task to ensure compliance"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    todo_id: UUID = Field(default_factory=uuid4)
    meeting_id: UUID = Field(description="Reference to the meeting where to-do was identified")
    
    # To-do content
    title: str = Field(min_length=1, description="Brief title describing the to-do")
    description: str = Field(min_length=1, description="Detailed description of what needs to be done")
    
    # Parent relationship - to-dos can optionally reference a parent rock
    parent_rock_id: Optional[UUID] = Field(default=None, description="Optional reference to parent rock (to-dos are parallel, not nested)")
    
    # Assignment
    owner: str = Field(description="Person responsible for completing the to-do")
    owner_id: UUID = Field(description="ID of the person responsible")
    
    # Timeline - to-dos are 1-2 weeks maximum
    due_date: date = Field(description="Target completion date (within 1-2 weeks)")
    estimated_hours: Optional[int] = Field(default=None, ge=1, le=80, description="Estimated hours to complete (max 2 weeks = 80 hours)")
    
    # Completion tracking
    status: Literal["pending", "in_progress", "completed"] = Field(
        default="pending", 
        description="Current status of the to-do"
    )
    
    # Content and context
    summary: str = Field(description="AI-generated summary of the to-do and its context")
    
    # Meeting context
    mentioned_by: Optional[str] = Field(None, description="Person who mentioned this to-do in the meeting")
    timestamp: Optional[str] = Field(None, description="Timestamp when to-do was discussed (HH:MM:SS)")
    
    # Additional metadata
    dependencies: List[str] = Field(default_factory=list, description="Dependencies for this to-do")
    deliverables: List[str] = Field(default_factory=list, description="Expected deliverables")
    stakeholders: List[str] = Field(default_factory=list, description="Stakeholders who need to be informed")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None, description="When the to-do was completed")

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

    def is_overdue(self) -> bool:
        """Check if to-do is overdue"""
        if self.status == "completed":
            return False
        return date.today() > self.due_date

    def get_time_remaining(self) -> int:
        """Get days remaining until due date"""
        if self.status == "completed":
            return 0
        delta = self.due_date - date.today()
        return max(0, delta.days)

    def mark_completed(self) -> None:
        """Mark to-do as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def validate_timeframe(self) -> List[str]:
        """Validate that to-do fits within 1-2 week timeframe"""
        issues = []
        
        if self.due_date:
            days_from_now = (self.due_date - date.today()).days
            if days_from_now > 14:
                issues.append("To-dos should be completed within 1-2 weeks (14 days)")
            elif days_from_now < 0:
                issues.append("Due date cannot be in the past")
        
        if self.estimated_hours and self.estimated_hours > 80:
            issues.append("To-dos should not require more than 80 hours (2 weeks of work)")
            
        return issues

class ToDoCreateRequest(BaseModel):
    """Request model for creating a new to-do"""
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    parent_rock_id: Optional[UUID] = None
    owner: str
    owner_id: UUID
    due_date: date
    estimated_hours: Optional[int] = None
    dependencies: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)
    stakeholders: List[str] = Field(default_factory=list)
    mentioned_by: Optional[str] = None
    timestamp: Optional[str] = None

class ToDoUpdateRequest(BaseModel):
    """Request model for updating a to-do"""
    title: Optional[str] = None
    description: Optional[str] = None
    parent_rock_id: Optional[UUID] = None
    owner: Optional[str] = None
    owner_id: Optional[UUID] = None
    due_date: Optional[date] = None
    estimated_hours: Optional[int] = None
    status: Optional[Literal["pending", "in_progress", "completed"]] = None
    dependencies: Optional[List[str]] = None
    deliverables: Optional[List[str]] = None
    stakeholders: Optional[List[str]] = None
    summary: Optional[str] = None
