from typing import List, Dict, Any, Literal, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime

class User(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        from_attributes=True
    )

    employee_name: str
    employee_email: EmailStr
    employee_password: str
    employee_role: Literal["admin", "employee"] = "employee"
    employee_id: UUID = Field(default_factory=uuid4)
    assigned_rocks: Optional[List[UUID]] = Field(default_factory=list, description="Optional list of assigned rock UUIDs")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values, ObjectId and password"""
        kwargs["exclude_none"] = True
        kwargs["exclude"] = {"employee_password", *(kwargs.get("exclude", set()))}
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data 