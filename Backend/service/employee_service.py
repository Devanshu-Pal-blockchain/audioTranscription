from typing import Dict, List, Optional
from uuid import UUID, uuid4
from .db import db
from datetime import datetime

class EmployeeService:
    collection = db.employee_mappings

    @staticmethod
    async def get_employee_uuid(emp_id: str) -> Optional[str]:
        """Get UUID for an employee based on their empId"""
        mapping = await EmployeeService.collection.find_one({"empId": emp_id})
        return mapping.get("uuid") if mapping else None

    @staticmethod
    async def create_or_get_uuid(emp_id: str) -> str:
        """Create or retrieve UUID for an employee"""
        existing = await EmployeeService.get_employee_uuid(emp_id)
        if existing:
            return existing

        # Create new UUID mapping
        uuid = str(uuid4())
        await EmployeeService.collection.insert_one({
            "empId": emp_id,
            "uuid": uuid,
            "created_at": datetime.utcnow()
        })
        return uuid

    @staticmethod
    async def get_all_mappings() -> List[Dict]:
        """Get all employee ID to UUID mappings"""
        mappings = []
        async for mapping in EmployeeService.collection.find({}):
            mappings.append({
                "empId": mapping["empId"],
                "uuid": mapping["uuid"]
            })
        return mappings

    @staticmethod
    async def update_employee_data(emp_id: str, data: Dict) -> bool:
        """Update additional employee data"""
        try:
            await EmployeeService.collection.update_one(
                {"empId": emp_id},
                {"$set": {
                    "employee_data": data,
                    "updated_at": datetime.utcnow()
                }}
            )
            return True
        except Exception:
            return False 