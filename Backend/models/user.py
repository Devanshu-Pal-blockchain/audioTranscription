from typing import List, Dict, Any, Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from datetime import datetime

class User(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat()
        },
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "employee_name": "John Doe",
                "employee_email": "john.doe@company.com",
                "employee_password": "hashed_password_here",
                "employee_role": "employee",
                "assigned_rocks": []
            }
        }
    )

    id: UUID = Field(default_factory=uuid4)
    employee_id: UUID = Field(default_factory=uuid4)
    employee_name: str = Field(min_length=1, description="Employee name")
    employee_email: EmailStr = Field(description="Employee email")
    employee_password: str = Field(min_length=8, description="Hashed password")
    employee_role: Literal["admin", "employee"] = Field(description="Employee role")
    assigned_rocks: List[UUID] = Field(default_factory=list, description="List of assigned rock IDs")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values, ObjectId and password"""
        kwargs["exclude_none"] = True
        kwargs["exclude"] = {"employee_password", *(kwargs.get("exclude", set()))}
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data 