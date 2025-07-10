from typing import Dict, Any, Optional, Literal, List
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime, date

class SolutionTimeline(BaseModel):
    """Timeline information for solutions"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        }
    )
    
    start_date: date = Field(description="Solution start date")
    end_date: date = Field(description="Solution target completion date")
    duration_days: int = Field(ge=0, description="Duration in days")

class Solution(BaseModel):
    """Solution model for IDS system - covers runtime solutions, to-dos, and rocks"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "solution_id": "123e4567-e89b-12d3-a456-426614174000",
                "solution_type": "todo",
                "meeting_id": "123e4567-e89b-12d3-a456-426614174001",
                "issue_reference": "123e4567-e89b-12d3-a456-426614174002",
                "title": "Provision additional cloud resources",
                "description": "Set up additional testing environments in AWS to resolve development bottleneck",
                "owner": "DevOps Team Lead",
                "timeline": {
                    "start_date": "2024-07-11",
                    "end_date": "2024-07-18",
                    "duration_days": 7
                },
                "status": "assigned",
                "summary": "Infrastructure solution to address testing environment shortage"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    solution_id: UUID = Field(default_factory=uuid4)
    solution_type: Literal["runtime", "todo", "rock"] = Field(description="Type of solution based on timeframe")
    meeting_id: UUID = Field(description="Reference to the meeting where solution was identified")
    
    # Related entities
    issue_reference: Optional[UUID] = Field(default=None, description="Reference to the issue this solution addresses")
    parent_rock: Optional[UUID] = Field(default=None, description="Parent rock for to-dos and sub-rocks")
    
    # Solution content
    title: str = Field(min_length=1, description="Brief title describing the solution")
    description: str = Field(min_length=1, description="Detailed description of the solution")
    owner: str = Field(description="Person responsible for implementing the solution")
    
    # Timeline and tracking
    timeline: SolutionTimeline = Field(description="Timeline information for the solution")
    status: Literal["identified", "assigned", "in_progress", "completed", "blocked", "cancelled", "deferred"] = Field(
        default="identified",
        description="Current status of the solution"
    )
    summary: str = Field(description="AI-generated summary of the solution and its context")
    
    # Progress tracking
    percentage_completion: int = Field(default=0, ge=0, le=100, description="Completion percentage")
    milestones: List[UUID] = Field(default_factory=list, description="List of milestone IDs for this solution")
    
    # Meeting context
    mentioned_by: Optional[str] = Field(default=None, description="Person who proposed the solution")
    timestamp: Optional[str] = Field(default=None, description="Timestamp in meeting when solution was discussed")
    
    # Additional metadata
    success_criteria: Optional[str] = Field(default=None, description="Criteria for measuring solution success")
    resources_required: Optional[List[str]] = Field(default_factory=list, description="Resources needed for implementation")
    dependencies: Optional[List[str]] = Field(default_factory=list, description="Dependencies that must be met")
    risk_assessment: Optional[str] = Field(default=None, description="Risk assessment for the solution")
    
    # SMART criteria for rocks
    smart_objective: Optional[str] = Field(default=None, description="SMART objective (required for rock type)")
    measurable_success: Optional[str] = Field(default=None, description="Measurable success criteria (required for rock type)")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None, description="When implementation started")
    completed_at: Optional[datetime] = Field(default=None, description="When solution was completed")

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

    def get_timeframe_category(self) -> str:
        """Determine timeframe category based on duration"""
        if self.timeline.duration_days == 0:
            return "runtime"
        elif 1 <= self.timeline.duration_days <= 14:
            return "todo"
        elif 15 <= self.timeline.duration_days <= 90:
            return "rock"
        else:
            return "long_term"

    def is_overdue(self) -> bool:
        """Check if solution is overdue"""
        if self.status in ["completed", "cancelled"]:
            return False
        return date.today() > self.timeline.end_date

    def update_progress(self, percentage: int) -> None:
        """Update progress percentage"""
        self.percentage_completion = max(0, min(100, percentage))
        self.updated_at = datetime.utcnow()
        
        if percentage == 100:
            self.status = "completed"
            self.completed_at = datetime.utcnow()

    def start_implementation(self) -> None:
        """Mark solution as started"""
        self.status = "in_progress"
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def complete_solution(self) -> None:
        """Mark solution as completed"""
        self.status = "completed"
        self.percentage_completion = 100
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def validate_rock_requirements(self) -> bool:
        """Validate that rock-type solutions have required fields"""
        if self.solution_type == "rock":
            return bool(self.smart_objective and self.measurable_success)
        return True
