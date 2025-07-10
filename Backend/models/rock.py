from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime

class Rock(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "rock_name": "Increase Market Share",
                "smart_objective": "Increase market share by 15% in APAC region by Q2 2024",
                "quarter_id": "123e4567-e89b-12d3-a456-426614174000",
                "assigned_to_id": "123e4567-e89b-12d3-a456-426614174001",
                "assigned_to_name": "John Doe"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    rock_id: UUID = Field(default_factory=uuid4)
    rock_name: str = Field(min_length=1, description="Name of the rock/goal")
    smart_objective: str = Field(min_length=1, description="SMART objective description")
    quarter_id: UUID = Field(description="Reference to parent quarter")
    assigned_to_id: UUID = Field(description="ID of the assigned user")
    assigned_to_name: str = Field(description="Name of the assigned user")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

class PipelineRock(BaseModel):
    rock_id: str
    smart_rock: str
    quarter_id: str
    owner_id: str
    owner_name: str
    designation: str
    linked_issues: List[str] = []

class PipelineMilestone(BaseModel):
    rock_id: str
    week: int
    milestone_id: str
    milestone: str

class PipelineTodo(BaseModel):
    todo_id: str
    to_do: str
    owner: str
    owner_id: str
    designation: str
    due_date: str
    linked_issue: str

class PipelineIssue(BaseModel):
    issue_id: str
    issue: str
    owner: str
    owner_id: str
    linked_solution_type: str
    linked_solution_ref: str

class PipelineRuntimeSolution(BaseModel):
    solution_id: str
    solution_title: str
    description: str
    owner: str
    owner_id: str
    designation: str
    deadline: str 