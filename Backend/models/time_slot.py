from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime

class TimeSlot(BaseModel):
    """Time slot model for temporal analysis of meeting discussions"""
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "slot_id": "123e4567-e89b-12d3-a456-426614174000",
                "meeting_id": "123e4567-e89b-12d3-a456-426614174001",
                "start_time": "00:15:30",
                "end_time": "00:18:45",
                "duration_seconds": 195,
                "topic": "Resource allocation discussion",
                "participants": ["John Doe", "Jane Smith"],
                "category": "issues",
                "key_points": [
                    "Development team blocked by insufficient cloud resources",
                    "Testing environment capacity at maximum",
                    "Need additional AWS instances"
                ],
                "outcomes": [
                    "Identified infrastructure bottleneck",
                    "Assigned DevOps team to assess requirements"
                ]
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    slot_id: UUID = Field(default_factory=uuid4)
    meeting_id: UUID = Field(description="Reference to the meeting this time slot belongs to")
    
    # Time boundaries
    start_time: str = Field(description="Start time in format HH:MM:SS")
    end_time: str = Field(description="End time in format HH:MM:SS")
    duration_seconds: int = Field(ge=0, description="Duration of the time slot in seconds")
    
    # Content classification
    topic: str = Field(min_length=1, description="Main topic discussed during this time slot")
    category: Literal["issues", "solutions", "decisions", "planning", "discussion", "review", "other"] = Field(
        description="Category of discussion during this time slot"
    )
    
    # Participants and content
    participants: List[str] = Field(default_factory=list, description="Active speakers during this time slot")
    key_points: List[str] = Field(default_factory=list, description="Main discussion points")
    outcomes: List[str] = Field(default_factory=list, description="Results or outcomes from this discussion")
    
    # Extracted entities
    issues_identified: List[UUID] = Field(default_factory=list, description="Issues identified in this time slot")
    solutions_proposed: List[UUID] = Field(default_factory=list, description="Solutions proposed in this time slot")
    decisions_made: List[str] = Field(default_factory=list, description="Decisions made during this time slot")
    
    # Content analysis
    sentiment: Optional[Literal["positive", "neutral", "negative"]] = Field(
        default=None, 
        description="Overall sentiment of the discussion"
    )
    urgency_level: Literal["low", "medium", "high", "critical"] = Field(
        default="medium",
        description="Urgency level of topics discussed"
    )
    
    # Meeting flow context
    previous_slot: Optional[UUID] = Field(default=None, description="Previous time slot ID for sequence")
    next_slot: Optional[UUID] = Field(default=None, description="Next time slot ID for sequence")
    
    # Transcript reference
    transcript_segment: Optional[str] = Field(default=None, description="Raw transcript segment for this time slot")
    
    # Additional metadata
    action_items_generated: List[str] = Field(default_factory=list, description="Action items identified")
    follow_up_required: bool = Field(default=False, description="Whether this topic needs follow-up")
    priority_rating: int = Field(default=3, ge=1, le=5, description="Priority rating (1-5) for topics discussed")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

    def get_duration_minutes(self) -> float:
        """Get duration in minutes"""
        return self.duration_seconds / 60.0

    def get_time_range_display(self) -> str:
        """Get formatted time range for display"""
        return f"{self.start_time} - {self.end_time}"

    def add_issue(self, issue_id: UUID) -> None:
        """Add an issue reference to this time slot"""
        if issue_id not in self.issues_identified:
            self.issues_identified.append(issue_id)
            self.updated_at = datetime.utcnow()

    def add_solution(self, solution_id: UUID) -> None:
        """Add a solution reference to this time slot"""
        if solution_id not in self.solutions_proposed:
            self.solutions_proposed.append(solution_id)
            self.updated_at = datetime.utcnow()

    def add_key_point(self, point: str) -> None:
        """Add a key discussion point"""
        if point not in self.key_points:
            self.key_points.append(point)
            self.updated_at = datetime.utcnow()

    def add_outcome(self, outcome: str) -> None:
        """Add an outcome from this discussion"""
        if outcome not in self.outcomes:
            self.outcomes.append(outcome)
            self.updated_at = datetime.utcnow()

    def calculate_engagement_score(self) -> float:
        """Calculate engagement score based on participants and content"""
        base_score = len(self.participants) * 10
        content_score = len(self.key_points) * 5 + len(self.outcomes) * 10
        action_score = len(self.action_items_generated) * 15
        
        total_score = base_score + content_score + action_score
        # Normalize to 0-100 scale
        return min(100, total_score)

    def is_high_priority(self) -> bool:
        """Check if this time slot contains high priority content"""
        return (
            self.urgency_level in ["high", "critical"] or
            self.priority_rating >= 4 or
            len(self.issues_identified) > 0 or
            len(self.action_items_generated) > 2
        )
