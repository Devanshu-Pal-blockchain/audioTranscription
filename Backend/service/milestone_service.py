from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from motor.motor_asyncio import AsyncIOMotorCollection
from models.milestone import Milestone
from .db import get_database

class MilestoneService:
    @staticmethod
    async def get_collection() -> AsyncIOMotorCollection:
        """Get the milestones collection"""
        db = await get_database()
        return db.milestones

    @staticmethod
    async def create_milestone(milestone_data: Dict[str, Any]) -> Milestone:
        """Create a new milestone"""
        collection = await MilestoneService.get_collection()
        
        # Create milestone instance
        milestone = Milestone(**milestone_data)
        
        # Insert into database
        result = await collection.insert_one(milestone.model_dump())
        
        if result.inserted_id:
            return milestone
        else:
            raise Exception("Failed to create milestone")

    @staticmethod
    async def get_milestone(milestone_id: UUID) -> Optional[Milestone]:
        """Get a milestone by ID"""
        collection = await MilestoneService.get_collection()
        
        milestone_data = await collection.find_one({"milestone_id": milestone_id})
        if milestone_data:
            milestone_data.pop("_id", None)
            return Milestone(**milestone_data)
        return None

    @staticmethod
    async def get_milestones_by_rock(parent_rock_id: UUID) -> List[Milestone]:
        """Get all milestones for a specific rock"""
        collection = await MilestoneService.get_collection()
        
        cursor = collection.find({"parent_rock_id": parent_rock_id})
        milestones = []
        
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def get_milestones_by_week(week_number: int) -> List[Milestone]:
        """Get all milestones for a specific week"""
        collection = await MilestoneService.get_collection()
        
        cursor = collection.find({"week_number": week_number})
        milestones = []
        
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def get_milestones_by_assigned_to(assigned_to: str) -> List[Milestone]:
        """Get all milestones assigned to a specific person"""
        collection = await MilestoneService.get_collection()
        
        cursor = collection.find({"assigned_to": assigned_to})
        milestones = []
        
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def get_milestones_by_status(status: str) -> List[Milestone]:
        """Get all milestones by status"""
        collection = await MilestoneService.get_collection()
        
        cursor = collection.find({"status": status})
        milestones = []
        
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def get_milestones_by_priority(priority: str) -> List[Milestone]:
        """Get all milestones by priority"""
        collection = await MilestoneService.get_collection()
        
        cursor = collection.find({"priority": priority})
        milestones = []
        
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def get_completed_milestones() -> List[Milestone]:
        """Get all completed milestones"""
        collection = await MilestoneService.get_collection()
        
        cursor = collection.find({"check_completed": True})
        milestones = []
        
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def get_overdue_milestones() -> List[Milestone]:
        """Get all overdue milestones"""
        collection = await MilestoneService.get_collection()
        
        # Find milestones with due_date in the past and not completed/cancelled
        current_date = date.today()
        cursor = collection.find({
            "due_date": {"$lt": current_date},
            "status": {"$nin": ["completed", "cancelled"]},
            "check_completed": False
        })
        
        milestones = []
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def get_milestones_due_soon(days: int = 7) -> List[Milestone]:
        """Get milestones due within specified number of days"""
        collection = await MilestoneService.get_collection()
        
        from datetime import timedelta
        target_date = date.today() + timedelta(days=days)
        
        cursor = collection.find({
            "due_date": {"$lte": target_date, "$gte": date.today()},
            "status": {"$nin": ["completed", "cancelled"]},
            "check_completed": False
        })
        
        milestones = []
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def update_milestone(milestone_id: UUID, update_data: Dict[str, Any]) -> Optional[Milestone]:
        """Update a milestone"""
        collection = await MilestoneService.get_collection()
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"milestone_id": milestone_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await MilestoneService.get_milestone(milestone_id)
        return None

    @staticmethod
    async def update_milestone_status(milestone_id: UUID, status: str) -> Optional[Milestone]:
        """Update milestone status"""
        update_data = {"status": status}
        
        # Set timestamps based on status
        if status == "in_progress":
            update_data["started_at"] = datetime.utcnow()
        elif status == "completed":
            update_data["completed_at"] = datetime.utcnow()
            
        return await MilestoneService.update_milestone(milestone_id, update_data)

    @staticmethod
    async def mark_milestone_completed(milestone_id: UUID) -> Optional[Milestone]:
        """Mark milestone as completed"""
        update_data = {
            "status": "completed",
            "completed_at": datetime.utcnow()
        }
        return await MilestoneService.update_milestone(milestone_id, update_data)

    @staticmethod
    async def toggle_completion(milestone_id: UUID) -> Optional[Milestone]:
        """Toggle milestone completion status"""
        milestone = await MilestoneService.get_milestone(milestone_id)
        if not milestone:
            return None
            
        if milestone.status == "completed":
            # Mark as incomplete
            update_data = {
                "status": "pending",
                "completed_at": None
            }
        else:
            # Mark as complete
            update_data = {
                "status": "completed",
                "completed_at": datetime.utcnow()
            }
            
        return await MilestoneService.update_milestone(milestone_id, update_data)

    @staticmethod
    async def add_dependency(milestone_id: UUID, dependency: str) -> Optional[Milestone]:
        """Add a dependency to a milestone"""
        collection = await MilestoneService.get_collection()
        
        result = await collection.update_one(
            {"milestone_id": milestone_id},
            {
                "$addToSet": {"dependencies": dependency},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await MilestoneService.get_milestone(milestone_id)
        return None

    @staticmethod
    async def remove_dependency(milestone_id: UUID, dependency: str) -> Optional[Milestone]:
        """Remove a dependency from a milestone"""
        collection = await MilestoneService.get_collection()
        
        result = await collection.update_one(
            {"milestone_id": milestone_id},
            {
                "$pull": {"dependencies": dependency},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await MilestoneService.get_milestone(milestone_id)
        return None

    @staticmethod
    async def add_deliverable(milestone_id: UUID, deliverable: str) -> Optional[Milestone]:
        """Add a deliverable to a milestone"""
        collection = await MilestoneService.get_collection()
        
        result = await collection.update_one(
            {"milestone_id": milestone_id},
            {
                "$addToSet": {"deliverables": deliverable},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await MilestoneService.get_milestone(milestone_id)
        return None

    @staticmethod
    async def update_effort_tracking(milestone_id: UUID, estimated_hours: int = None, actual_hours: int = None) -> Optional[Milestone]:
        """Update effort tracking for a milestone"""
        update_data = {}
        if estimated_hours is not None:
            update_data["estimated_hours"] = estimated_hours
        if actual_hours is not None:
            update_data["actual_hours"] = actual_hours
            
        if update_data:
            return await MilestoneService.update_milestone(milestone_id, update_data)
        return None

    @staticmethod
    async def delete_milestone(milestone_id: UUID) -> bool:
        """Delete a milestone"""
        collection = await MilestoneService.get_collection()
        
        result = await collection.delete_one({"milestone_id": milestone_id})
        return result.deleted_count > 0

    @staticmethod
    async def get_all_milestones() -> List[Milestone]:
        """Get all milestones"""
        collection = await MilestoneService.get_collection()
        
        cursor = collection.find({})
        milestones = []
        
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def search_milestones(search_term: str) -> List[Milestone]:
        """Search milestones by title or description"""
        collection = await MilestoneService.get_collection()
        
        # Case-insensitive search in title and description
        cursor = collection.find({
            "$or": [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}}
            ]
        })
        
        milestones = []
        async for milestone_data in cursor:
            milestone_data.pop("_id", None)
            milestones.append(Milestone(**milestone_data))
            
        return milestones

    @staticmethod
    async def get_milestone_statistics() -> Dict[str, Any]:
        """Get milestone statistics"""
        collection = await MilestoneService.get_collection()
        
        # Count by status
        statuses = ["pending", "in_progress", "completed", "blocked", "deferred", "cancelled"]
        status_counts = {}
        for status in statuses:
            status_counts[status] = await collection.count_documents({"status": status})
        
        # Count by priority
        priorities = ["critical", "high", "medium", "low"]
        priority_counts = {}
        for priority in priorities:
            priority_counts[priority] = await collection.count_documents({"priority": priority})
        
        # Count completed vs not completed
        completed_count = await collection.count_documents({"check_completed": True})
        pending_count = await collection.count_documents({"check_completed": False})
        
        # Count overdue milestones
        current_date = date.today()
        overdue_count = await collection.count_documents({
            "due_date": {"$lt": current_date},
            "status": {"$nin": ["completed", "cancelled"]},
            "check_completed": False
        })
        
        # Average completion percentage
        pipeline = [
            {"$group": {"_id": None, "avg_completion": {"$avg": "$percentage_completion"}}}
        ]
        avg_result = await collection.aggregate(pipeline).to_list(1)
        avg_completion = avg_result[0]["avg_completion"] if avg_result else 0
        
        # Total count
        total_count = await collection.count_documents({})
        
        return {
            "by_status": status_counts,
            "by_priority": priority_counts,
            "completion": {
                "completed": completed_count,
                "pending": pending_count,
                "completion_rate": round((completed_count / total_count * 100), 2) if total_count > 0 else 0
            },
            "overdue": overdue_count,
            "average_completion": round(avg_completion, 2),
            "total": total_count
        }

    @staticmethod
    async def bulk_create_milestones(milestones_data: List[Dict[str, Any]]) -> List[Milestone]:
        """Bulk create multiple milestones"""
        collection = await MilestoneService.get_collection()
        
        # Create milestone instances
        milestones = [Milestone(**milestone_data) for milestone_data in milestones_data]
        
        # Bulk insert
        milestone_dicts = [milestone.model_dump() for milestone in milestones]
        result = await collection.insert_many(milestone_dicts)
        
        if result.inserted_ids:
            return milestones
        else:
            raise Exception("Failed to create milestones")

    @staticmethod
    async def bulk_update_status(milestone_ids: List[UUID], status: str) -> int:
        """Bulk update status for multiple milestones"""
        collection = await MilestoneService.get_collection()
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        # Add appropriate timestamps and completion based on status
        if status == "in_progress":
            update_data["started_at"] = datetime.utcnow()
        elif status == "completed":
            update_data["completed_at"] = datetime.utcnow()
            update_data["check_completed"] = True
            update_data["percentage_completion"] = 100
        
        result = await collection.update_many(
            {"milestone_id": {"$in": milestone_ids}},
            {"$set": update_data}
        )
        
        return result.modified_count

    @staticmethod
    async def bulk_toggle_completion(milestone_ids: List[UUID]) -> int:
        """Bulk toggle completion for multiple milestones"""
        collection = await MilestoneService.get_collection()
        
        modified_count = 0
        for milestone_id in milestone_ids:
            result = await MilestoneService.toggle_completion(milestone_id)
            if result:
                modified_count += 1
                
        return modified_count
