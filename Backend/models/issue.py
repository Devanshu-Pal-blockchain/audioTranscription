from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class Issue(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "issue_id": "123e4567-e89b-12d3-a456-426614174000",
                "issue_title": "Resource allocation bottleneck",
                "description": "Team capacity constraints affecting project delivery",
                "raised_by": "John Doe",
                "discussion_notes": "Discussed multiple solutions including hiring and process optimization",
                "linked_solution_type": "rock",
                "linked_solution_ref": "Optimize team structure for Q2",
                "status": "open",
                "quarter_id": "123e4567-e89b-12d3-a456-426614174001"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    issue_id: UUID = Field(default_factory=uuid4)
    issue_title: str = Field(min_length=1, description="Title of the issue")
    description: str = Field(default="", description="Detailed description of the issue")
    raised_by: str = Field(min_length=1, description="Full name of the person who raised the issue")
    discussion_notes: Optional[str] = Field(default=None, description="Key discussion points about the issue")
    linked_solution_type: Optional[str] = Field(default=None, description="Type of solution: rock, todo, or runtime_solution")
    linked_solution_ref: Optional[str] = Field(default=None, description="Reference to the related solution")
    status: str = Field(default="open", description="Status of the issue (open, in_progress, resolved)")
    quarter_id: UUID = Field(description="Reference to the quarter this issue belongs to")
    raised_by_id: Optional[UUID] = Field(default=None, description="UUID of the person who raised the issue if available")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

class PipelineIssue(BaseModel):
    """Model for issues from pipeline response"""
    issue_title: str
    description: str
    raised_by: str
    discussion_notes: Optional[str] = None
    linked_solution_type: Optional[str] = None
    linked_solution_ref: Optional[str] = None
