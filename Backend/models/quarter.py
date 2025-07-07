from typing import List, Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime

class Quarter(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "quarter_id": "123e4567-e89b-12d3-a456-426614174000",
                "quarter": "Q1",
                "weeks": 12,
                "year": 2024,
                "title": "First Quarter Planning",
                "description": "Strategic planning for Q1 2024",
                "participants": ["123e4567-e89b-12d3-a456-426614174001"],
                "status": 0,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00"
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    quarter: str = Field(description="Quarter identifier (Q1, Q2, Q3, Q4)", pattern="^Q[1-4]$")
    weeks: int = Field(gt=0, description="Number of weeks in the quarter")
    year: int = Field(gt=1900, lt=10000, description="Year of the quarter")
    title: str = Field(min_length=1, description="Quarter title")
    description: str = Field(default="", description="Quarter description")
    participants: List[UUID] = Field(default_factory=list, description="List of participant UUIDs")
    status: int = Field(default=0, description="Quarter status (0 = draft, 1 = saved)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values and ObjectId"""
        kwargs["exclude_none"] = True
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data 