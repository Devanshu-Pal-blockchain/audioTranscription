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

    employee_id: UUID = Field(default_factory=uuid4)
    employee_name: str
    employee_email: EmailStr
    employee_password: str
    employee_role: Literal["facilitator", "employee"] = "employee"  # facilitator or employee (C-level executives)
    employee_responsibilities: Optional[str] = None
    employee_code: Optional[str] = None
    employee_designation: Optional[str] = None
    
    # Enhanced rock assignments for VTO
    assigned_rocks: Optional[List[UUID]] = Field(default_factory=list, description="Legacy field for backward compatibility")
    annual_rocks: List[UUID] = Field(default_factory=list, description="Annual rocks assigned to user")
    company_rocks: List[UUID] = Field(default_factory=list, description="Company rocks assigned to user") 
    individual_rocks: List[UUID] = Field(default_factory=list, description="Individual rocks assigned to user")
    
    # Meeting participation tracking
    meetings_participated: List[UUID] = Field(default_factory=list, description="Meetings this user has participated in")
    
    # VTO role and permissions
    vto_role: Optional[Literal["facilitator", "participant", "observer"]] = Field(
        default="participant",
        description="Role in VTO meetings"
    )
    can_create_annual_rocks: bool = Field(default=False, description="Permission to create annual rocks")
    can_edit_company_rocks: bool = Field(default=False, description="Permission to edit company rocks")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump method to exclude None values, ObjectId and password"""
        kwargs["exclude_none"] = True
        kwargs["exclude"] = {"employee_password", *(kwargs.get("exclude", set()))}
        data = super().model_dump(*args, **kwargs)
        data.pop("_id", None)
        return data

    def get_total_rocks_count(self) -> int:
        """Get total number of rocks assigned to user"""
        return len(self.annual_rocks) + len(self.company_rocks) + len(self.individual_rocks)

    def assign_rock(self, rock_id: UUID, rock_type: str) -> None:
        """Assign a rock to the user based on rock type"""
        if rock_type == "annual" and rock_id not in self.annual_rocks:
            self.annual_rocks.append(rock_id)
        elif rock_type == "company" and rock_id not in self.company_rocks:
            self.company_rocks.append(rock_id)
        elif rock_type == "individual" and rock_id not in self.individual_rocks:
            self.individual_rocks.append(rock_id)
        
        # Update legacy field for backward compatibility
        if rock_id not in self.assigned_rocks:
            self.assigned_rocks.append(rock_id)
            
        self.updated_at = datetime.utcnow()

    def unassign_rock(self, rock_id: UUID, rock_type: str) -> None:
        """Remove a rock assignment from the user"""
        if rock_type == "annual" and rock_id in self.annual_rocks:
            self.annual_rocks.remove(rock_id)
        elif rock_type == "company" and rock_id in self.company_rocks:
            self.company_rocks.remove(rock_id)
        elif rock_type == "individual" and rock_id in self.individual_rocks:
            self.individual_rocks.remove(rock_id)
        
        # Update legacy field
        if rock_id in self.assigned_rocks:
            self.assigned_rocks.remove(rock_id)
            
        self.updated_at = datetime.utcnow()

    def can_create_rocks(self, rock_type: str) -> bool:
        """Check if user can create rocks of specified type"""
        if self.employee_role == "facilitator":
            return True
            
        if rock_type == "annual":
            return self.can_create_annual_rocks
        elif rock_type == "company":
            return self.can_edit_company_rocks
        else:  # individual rocks
            return True  # Users can create their own individual rocks

    def add_meeting_participation(self, meeting_id: UUID) -> None:
        """Add meeting to participation history"""
        if meeting_id not in self.meetings_participated:
            self.meetings_participated.append(meeting_id)
            self.updated_at = datetime.utcnow()

    def sync_legacy_assigned_rocks(self) -> None:
        """Sync all rock types to legacy assigned_rocks field for backward compatibility"""
        all_rocks = set(self.annual_rocks + self.company_rocks + self.individual_rocks)
        self.assigned_rocks = list(all_rocks)
        self.updated_at = datetime.utcnow()

    def get_rock_summary(self) -> Dict[str, int]:
        """Get summary of rock assignments by type"""
        return {
            "annual_rocks": len(self.annual_rocks),
            "company_rocks": len(self.company_rocks),
            "individual_rocks": len(self.individual_rocks),
            "total_rocks": self.get_total_rocks_count()
        }