from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime, date

class Todo(BaseModel):
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
                "task_title": "Finalize Q2 budget proposal",
                "assigned_to": "John Doe",
                "designation": "Finance Manager",
                "due_date": "2024-03-15",
                "linked_issue": "Budget allocation concerns",
                "status": "pending",
                "quarter_id": "123e4567-e89b-12d3-a456-426614174001"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    todo_id: UUID = Field(default_factory=uuid4)
    task_title: str = Field(min_length=1, description="Title of the todo task")
    assigned_to: str = Field(min_length=1, description="Full name of the person assigned")
    designation: str = Field(min_length=1, description="Job title/designation of the assigned person")
    due_date: date = Field(description="Due date for the todo")
    linked_issue: Optional[str] = Field(default=None, description="Title of the related issue")
    status: str = Field(default="pending", description="Status of the todo (pending, in_progress, completed)")
    quarter_id: UUID = Field(description="Reference to the quarter this todo belongs to")
    assigned_to_id: Optional[UUID] = Field(default=None, description="UUID of the assigned user if available")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

class PipelineTodo(BaseModel):
    """Model for todos from pipeline response"""
    task_title: str
    assigned_to: str
    designation: str
    due_date: str
    linked_issue: Optional[str] = None
