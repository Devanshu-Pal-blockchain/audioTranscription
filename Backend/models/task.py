from typing import Optional, Dict, Any, List, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime

class Comment(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "comment_id": "123e4567-e89b-12d3-a456-426614174000",
                "commented_by": "John Doe",
                "content": "Initial research completed for Singapore market",
                "is_admin_comment": False
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    comment_id: UUID = Field(default_factory=uuid4)
    commented_by: str = Field(description="Name/ID of the commenter")
    content: str = Field(min_length=1, description="Comment content")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_admin_comment: bool = Field(default=False, description="Whether this is an admin comment")

class Task(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "rock_id": "123e4567-e89b-12d3-a456-426614174000",
                "week": 1,
                "task": "Research current market share in APAC region",
                "sub_tasks": {
                    "1": "Gather data from existing markets",
                    "2": "Analyze competitor presence"
                },
                "comments": [
                    {
                        "commented_by": "John Doe",
                        "content": "Initial research completed for Singapore market",
                        "is_admin_comment": False
                    }
                ]
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    rock_id: UUID = Field(description="Reference to parent rock")
    week: int = Field(gt=0, description="Week number for this task")
    task_id: Union[UUID, str] = Field(default_factory=lambda: str(uuid4()), description="Task identifier (UUID or string)")
    task: str = Field(min_length=1, description="Task description")
    sub_tasks: Optional[Union[Dict[str, str], List]] = Field(default=None, description="Optional subtasks")
    comments: Union[List[Comment], Dict, List] = Field(default_factory=list, description="List of comments")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator('sub_tasks', mode='before')
    @classmethod
    def validate_sub_tasks(cls, v):
        """Convert empty list to None or dict for sub_tasks"""
        if v == []:
            return None
        elif isinstance(v, list) and len(v) == 0:
            return None
        return v

    @field_validator('comments', mode='before')
    @classmethod
    def validate_comments(cls, v):
        """Convert various comment formats to list of Comment objects"""
        if v is None or v == []:
            return []
        elif isinstance(v, dict):
            # Single comment object, convert to list
            if v.get('comment_id') == '' and v.get('commented_by') == '':
                return []  # Empty comment, return empty list
            return [v]
        elif isinstance(v, list):
            return v
        return []

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data 