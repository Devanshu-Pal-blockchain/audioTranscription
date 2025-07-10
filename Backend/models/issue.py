from typing import Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime

class Issue(BaseModel):
    """Issue model for IDS (Issues, Decisions, Solutions) system"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "issue_id": "123e4567-e89b-12d3-a456-426614174000",
                "meeting_id": "123e4567-e89b-12d3-a456-426614174001",
                "title": "Resource allocation bottleneck",
                "description": "Development team is blocked due to insufficient cloud resources for testing environment",
                "mentioned_by": "John Doe",
                "timestamp": "00:15:30",
                "status": "open",
                "summary": "Critical resource shortage affecting development velocity and testing capabilities"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    issue_id: UUID = Field(default_factory=uuid4)
    meeting_id: UUID = Field(description="Reference to the meeting where issue was identified")
    
    # Issue content
    title: str = Field(min_length=1, description="Brief title describing the issue")
    description: str = Field(min_length=1, description="Detailed description of the issue")
    
    # Meeting context
    mentioned_by: Optional[str] = Field(None, description="Person who mentioned the issue (only if certain)")
    timestamp: Optional[str] = Field(None, description="Timestamp when issue was discussed (HH:MM:SS)")
    
    # Issue management - simplified status
    status: Literal["open", "resolved"] = Field(
        default="open", 
        description="Whether the issue is resolved or still open"
    )
    summary: str = Field(description="AI-generated summary of the issue and its context")
    
    # Resolution tracking
    solution_reference: Optional[UUID] = Field(default=None, description="Reference to solution if addressed")
    follow_up_required: bool = Field(default=True, description="Whether this issue requires follow-up")
    follow_up_deadline: Optional[datetime] = Field(default=None, description="Deadline for follow-up action")
    
    # Additional metadata
    impact_assessment: Optional[str] = Field(default=None, description="Assessment of issue impact on organization")
    root_cause: Optional[str] = Field(default=None, description="Identified root cause of the issue")
    stakeholders: Optional[list[str]] = Field(default_factory=list, description="Stakeholders affected by this issue")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(default=None, description="When the issue was resolved")

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

    def mark_as_addressed(self, solution_id: UUID) -> None:
        """Mark issue as addressed with reference to solution"""
        self.status = "addressed"
        self.solution_reference = solution_id
        self.updated_at = datetime.utcnow()

    def mark_as_resolved(self) -> None:
        """Mark issue as resolved"""
        self.status = "resolved"
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def is_overdue(self) -> bool:
        """Check if issue follow-up is overdue"""
        if not self.follow_up_deadline:
            return False
        return datetime.utcnow() > self.follow_up_deadline and self.status == "open"
