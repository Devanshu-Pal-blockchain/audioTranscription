from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime, date

class Rock(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "rock_name": "Increase Market Share",
                "rock_type": "company",
                "measurable_success": "Achieve 15% market share in APAC region measured by quarterly revenue reports",
                "quarter_id": "123e4567-e89b-12d3-a456-426614174000",
                "owner_id": "123e4567-e89b-12d3-a456-426614174001",
                "owner": "John Doe",
                "percentage_completion": 25,
                "meeting_id": "123e4567-e89b-12d3-a456-426614174002"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    rock_id: UUID = Field(default_factory=uuid4)
    
    # Enhanced rock classification for VTO
    rock_type: Literal["annual", "company", "individual"] = Field(
        description="Type of rock in VTO system"
    )
    rock_name: str = Field(min_length=1, description="Rock name/objective (rocks are inherently SMART)")
    
    # VTO-specific fields  
    measurable_success: str = Field(min_length=1, description="Measurable success criteria for all rock types")
    percentage_completion: int = Field(default=0, ge=0, le=100, description="Completion percentage")
    
    # Relationships
    quarter_id: Optional[UUID] = Field(default=None, description="Reference to parent quarter (for quarterly rocks)")
    meeting_id: UUID = Field(description="Reference to source meeting")
    parent_rock: Optional[UUID] = Field(default=None, description="Parent rock for individual rocks")
    
    # Assignment (ownership)
    owner: str = Field(description="Owner of the rock (replaces assigned_to terminology)")
    owner_id: UUID = Field(description="ID of the owner")
    
    # Legacy fields for backward compatibility
    assigned_to_id: UUID = Field(description="ID of the assigned user (legacy, maps to owner_id)")
    assigned_to_name: str = Field(description="Name of the assigned user (legacy, maps to owner)")
    
    # Timeline
    start_date: Optional[date] = Field(default=None, description="Rock start date")
    end_date: Optional[date] = Field(default=None, description="Rock target completion date")
    duration_days: Optional[int] = Field(default=None, ge=0, description="Duration in days")
    
    # Milestone tracking
    weekly_milestones: List[UUID] = Field(default_factory=list, description="References to milestone collection")
    
    # Status and priority
    status: Literal["draft", "active", "completed", "blocked", "deferred", "cancelled"] = Field(
        default="draft",
        description="Current status of the rock"
    )
    priority: Literal["high", "medium", "low", "critical"] = Field(default="medium", description="Priority level")
    
    # Additional VTO metadata
    annual_rock_parent: Optional[UUID] = Field(default=None, description="Reference to parent annual rock")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies for this rock")
    success_metrics: List[str] = Field(default_factory=list, description="Key metrics for measuring success")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

    def is_overdue(self) -> bool:
        """Check if rock is overdue"""
        if self.status in ["completed", "cancelled"]:
            return False
        if not self.end_date:
            return False
        return date.today() > self.end_date

    def get_time_remaining(self) -> int:
        """Get days remaining until end date"""
        if self.status == "completed" or not self.end_date:
            return 0
        delta = self.end_date - date.today()
        return max(0, delta.days)

    def update_progress(self, percentage: int) -> None:
        """Update progress percentage"""
        self.percentage_completion = max(0, min(100, percentage))
        self.updated_at = datetime.utcnow()
        
        if percentage == 100:
            self.status = "completed"

    def get_rock_type_display(self) -> str:
        """Get human-readable rock type"""
        type_mapping = {
            "annual": "Annual Rock",
            "company": "Company Rock", 
            "individual": "Individual Rock"
        }
        return type_mapping.get(self.rock_type, self.rock_type.title())

    def validate_vto_requirements(self) -> List[str]:
        """Validate VTO-specific requirements and return any issues"""
        issues = []
        
        if not self.measurable_success:
            issues.append("Measurable success criteria required for VTO rocks")
            
        if self.rock_type == "annual" and self.duration_days and self.duration_days > 365:
            issues.append("Annual rocks should not exceed 365 days")
            
        if self.rock_type in ["company", "individual"] and self.duration_days and self.duration_days > 90:
            issues.append("Quarterly rocks should not exceed 90 days")
            
        return issues

    def sync_legacy_fields(self) -> None:
        """Sync new owner fields with legacy assigned_to fields for backward compatibility"""
        self.assigned_to_id = self.owner_id
        self.assigned_to_name = self.owner
        self.updated_at = datetime.utcnow()