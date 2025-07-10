from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from models.issue import Issue
from .db import get_database

class IssueService:
    @staticmethod
    async def get_collection() -> AsyncIOMotorCollection:
        """Get the issues collection"""
        db = await get_database()
        return db.issues

    @staticmethod
    async def create_issue(issue_data: Dict[str, Any]) -> Issue:
        """Create a new issue"""
        collection = await IssueService.get_collection()
        
        # Create issue instance
        issue = Issue(**issue_data)
        
        # Insert into database
        result = await collection.insert_one(issue.model_dump())
        
        if result.inserted_id:
            return issue
        else:
            raise Exception("Failed to create issue")

    @staticmethod
    async def get_issue(issue_id: UUID) -> Optional[Issue]:
        """Get an issue by ID"""
        collection = await IssueService.get_collection()
        
        issue_data = await collection.find_one({"issue_id": issue_id})
        if issue_data:
            issue_data.pop("_id", None)
            return Issue(**issue_data)
        return None

    @staticmethod
    async def get_issues_by_meeting(meeting_id: UUID) -> List[Issue]:
        """Get all issues from a specific meeting"""
        collection = await IssueService.get_collection()
        
        cursor = collection.find({"meeting_id": meeting_id})
        issues = []
        
        async for issue_data in cursor:
            issue_data.pop("_id", None)
            issues.append(Issue(**issue_data))
            
        return issues



    @staticmethod
    async def get_issues_by_status(status: str) -> List[Issue]:
        """Get all issues by status"""
        collection = await IssueService.get_collection()
        
        cursor = collection.find({"status": status})
        issues = []
        
        async for issue_data in cursor:
            issue_data.pop("_id", None)
            issues.append(Issue(**issue_data))
            
        return issues

    @staticmethod
    async def get_open_issues() -> List[Issue]:
        """Get all open issues"""
        return await IssueService.get_issues_by_status("open")

    @staticmethod
    async def get_overdue_issues() -> List[Issue]:
        """Get all overdue issues"""
        collection = await IssueService.get_collection()
        
        # Find issues with follow_up_deadline in the past and status still open
        current_time = datetime.utcnow()
        cursor = collection.find({
            "follow_up_deadline": {"$lt": current_time},
            "status": "open"
        })
        
        issues = []
        async for issue_data in cursor:
            issue_data.pop("_id", None)
            issues.append(Issue(**issue_data))
            
        return issues

    @staticmethod
    async def update_issue(issue_id: UUID, update_data: Dict[str, Any]) -> Optional[Issue]:
        """Update an issue"""
        collection = await IssueService.get_collection()
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"issue_id": issue_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await IssueService.get_issue(issue_id)
        return None

    @staticmethod
    async def update_issue_status(issue_id: UUID, status: str) -> Optional[Issue]:
        """Update issue status"""
        update_data = {"status": status}
        
        # Set resolved_at if marking as resolved
        if status == "resolved":
            update_data["resolved_at"] = datetime.utcnow()
            
        return await IssueService.update_issue(issue_id, update_data)

    @staticmethod
    async def mark_issue_resolved(issue_id: UUID, solution_id: UUID = None) -> Optional[Issue]:
        """Mark issue as resolved with optional solution reference"""
        update_data = {
            "status": "resolved",
            "resolved_at": datetime.utcnow()
        }
        if solution_id:
            update_data["solution_reference"] = solution_id
        return await IssueService.update_issue(issue_id, update_data)

    @staticmethod
    async def set_follow_up_deadline(issue_id: UUID, deadline: datetime) -> Optional[Issue]:
        """Set follow-up deadline for an issue"""
        return await IssueService.update_issue(issue_id, {"follow_up_deadline": deadline})

    @staticmethod
    async def add_stakeholder(issue_id: UUID, stakeholder: str) -> Optional[Issue]:
        """Add a stakeholder to an issue"""
        collection = await IssueService.get_collection()
        
        result = await collection.update_one(
            {"issue_id": issue_id},
            {
                "$addToSet": {"stakeholders": stakeholder},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await IssueService.get_issue(issue_id)
        return None

    @staticmethod
    async def remove_stakeholder(issue_id: UUID, stakeholder: str) -> Optional[Issue]:
        """Remove a stakeholder from an issue"""
        collection = await IssueService.get_collection()
        
        result = await collection.update_one(
            {"issue_id": issue_id},
            {
                "$pull": {"stakeholders": stakeholder},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await IssueService.get_issue(issue_id)
        return None

    @staticmethod
    async def delete_issue(issue_id: UUID) -> bool:
        """Delete an issue"""
        collection = await IssueService.get_collection()
        
        result = await collection.delete_one({"issue_id": issue_id})
        return result.deleted_count > 0

    @staticmethod
    async def get_all_issues() -> List[Issue]:
        """Get all issues"""
        collection = await IssueService.get_collection()
        
        cursor = collection.find({})
        issues = []
        
        async for issue_data in cursor:
            issue_data.pop("_id", None)
            issues.append(Issue(**issue_data))
            
        return issues

    @staticmethod
    async def search_issues(search_term: str) -> List[Issue]:
        """Search issues by title or description"""
        collection = await IssueService.get_collection()
        
        # Case-insensitive search in title and description
        cursor = collection.find({
            "$or": [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}}
            ]
        })
        
        issues = []
        async for issue_data in cursor:
            issue_data.pop("_id", None)
            issues.append(Issue(**issue_data))
            
        return issues

    @staticmethod
    async def get_issues_by_mentioned_by(mentioned_by: str) -> List[Issue]:
        """Get all issues mentioned by a specific person"""
        collection = await IssueService.get_collection()
        
        cursor = collection.find({"mentioned_by": mentioned_by})
        issues = []
        
        async for issue_data in cursor:
            issue_data.pop("_id", None)
            issues.append(Issue(**issue_data))
            
        return issues

    @staticmethod
    async def get_issue_statistics() -> Dict[str, Any]:
        """Get issue statistics"""
        collection = await IssueService.get_collection()
        
        # Count by status (simplified to open/resolved)
        status_counts = {
            "open": await collection.count_documents({"status": "open"}),
            "resolved": await collection.count_documents({"status": "resolved"})
        }
        
        # Count overdue issues
        current_time = datetime.utcnow()
        overdue_count = await collection.count_documents({
            "follow_up_deadline": {"$lt": current_time},
            "status": "open"
        })
        
        # Total count
        total_count = await collection.count_documents({})
        
        # Count by meeting type (VTO, L10, Annual, Quarterly)
        meeting_type_counts = {}
        pipeline = [
            {
                "$lookup": {
                    "from": "meetings",
                    "localField": "meeting_id",
                    "foreignField": "meeting_id", 
                    "as": "meeting_info"
                }
            },
            {
                "$unwind": "$meeting_info"
            },
            {
                "$group": {
                    "_id": "$meeting_info.meeting_type",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        async for result in collection.aggregate(pipeline):
            meeting_type_counts[result["_id"]] = result["count"]
        
        return {
            "by_status": status_counts,
            "by_meeting_type": meeting_type_counts,
            "overdue": overdue_count,
            "total": total_count
        }

    @staticmethod
    async def bulk_create_issues(issues_data: List[Dict[str, Any]]) -> List[Issue]:
        """Bulk create multiple issues"""
        collection = await IssueService.get_collection()
        
        # Create issue instances
        issues = [Issue(**issue_data) for issue_data in issues_data]
        
        # Bulk insert
        issue_dicts = [issue.model_dump() for issue in issues]
        result = await collection.insert_many(issue_dicts)
        
        if result.inserted_ids:
            return issues
        else:
            raise Exception("Failed to create issues")

    @staticmethod
    async def bulk_update_status(issue_ids: List[UUID], status: str) -> int:
        """Bulk update status for multiple issues"""
        collection = await IssueService.get_collection()
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        # Add resolved_at if marking as resolved
        if status == "resolved":
            update_data["resolved_at"] = datetime.utcnow()
        
        result = await collection.update_many(
            {"issue_id": {"$in": issue_ids}},
            {"$set": update_data}
        )
        
        return result.modified_count
