from typing import List, Optional, Dict
from uuid import UUID
from fastapi import HTTPException
from models.issue import Issue
from .base_service import BaseService
from datetime import datetime

class IssueService(BaseService):
    """Service for managing issues"""

    @staticmethod
    async def create_issue(issue: Issue) -> Issue:
        """Create a new issue"""
        # Validate quarter exists
        quarter_dict = await IssueService.quarters.find_one({"id": str(issue.quarter_id)})
        if not quarter_dict:
            raise HTTPException(status_code=404, detail="Quarter not found")
        
        issue_dict = issue.model_dump()
        await IssueService.issues.insert_one(issue_dict)
        return issue

    @staticmethod
    async def get_issue(issue_id: UUID) -> Optional[Issue]:
        """Get an issue by ID"""
        issue_dict = await IssueService.issues.find_one({"issue_id": str(issue_id)})
        if not issue_dict:
            return None
        return Issue(**issue_dict)

    @staticmethod
    async def get_issues_by_quarter(quarter_id: UUID) -> List[Issue]:
        """Get all issues for a specific quarter"""
        issues = []
        async for issue_dict in IssueService.issues.find({"quarter_id": str(quarter_id)}):
            issues.append(Issue(**issue_dict))
        return issues

    @staticmethod
    async def get_issues_by_user(raised_by_id: UUID) -> List[Issue]:
        """Get all issues raised by a specific user"""
        issues = []
        async for issue_dict in IssueService.issues.find({"raised_by_id": str(raised_by_id)}):
            issues.append(Issue(**issue_dict))
        return issues

    @staticmethod
    async def get_issues_by_status(status: str, quarter_id: Optional[UUID] = None) -> List[Issue]:
        """Get issues by status, optionally filtered by quarter"""
        filter_dict = {"status": status}
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        
        issues = []
        async for issue_dict in IssueService.issues.find(filter_dict):
            issues.append(Issue(**issue_dict))
        return issues

    @staticmethod
    async def get_issues_by_solution_type(solution_type: str, quarter_id: Optional[UUID] = None) -> List[Issue]:
        """Get issues by linked solution type"""
        filter_dict = {"linked_solution_type": solution_type}
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        
        issues = []
        async for issue_dict in IssueService.issues.find(filter_dict):
            issues.append(Issue(**issue_dict))
        return issues

    @staticmethod
    async def update_issue(issue_id: UUID, update_data: Dict) -> Optional[Issue]:
        """Update an issue"""
        # Remove fields that shouldn't be updated
        update_data.pop("id", None)
        update_data.pop("issue_id", None)
        update_data.pop("created_at", None)
        
        # Update timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await IssueService.issues.update_one(
            {"issue_id": str(issue_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            return None
        
        return await IssueService.get_issue(issue_id)

    @staticmethod
    async def delete_issue(issue_id: UUID) -> bool:
        """Delete an issue"""
        result = await IssueService.issues.delete_one({"issue_id": str(issue_id)})
        return result.deleted_count > 0

    @staticmethod
    async def search_issues(query: str, quarter_id: Optional[UUID] = None) -> List[Issue]:
        """Search issues by title or description"""
        filter_dict = {
            "$or": [
                {"issue_title": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"discussion_notes": {"$regex": query, "$options": "i"}}
            ]
        }
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        
        issues = []
        async for issue_dict in IssueService.issues.find(filter_dict):
            issues.append(Issue(**issue_dict))
        return issues

    @staticmethod
    async def bulk_create_issues(issues: List[Issue]) -> List[Issue]:
        """Create multiple issues at once"""
        if not issues:
            return []
        
        issue_dicts = [issue.model_dump() for issue in issues]
        await IssueService.issues.insert_many(issue_dicts)
        return issues

    @staticmethod
    async def get_issue_statistics(quarter_id: Optional[UUID] = None) -> Dict:
        """Get statistics about issues"""
        filter_dict = {}
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        
        total_issues = await IssueService.issues.count_documents(filter_dict)
        open_issues = await IssueService.issues.count_documents({**filter_dict, "status": "open"})
        in_progress_issues = await IssueService.issues.count_documents({**filter_dict, "status": "in_progress"})
        resolved_issues = await IssueService.issues.count_documents({**filter_dict, "status": "resolved"})
        
        # Count by solution type
        rock_issues = await IssueService.issues.count_documents({**filter_dict, "linked_solution_type": "rock"})
        todo_issues = await IssueService.issues.count_documents({**filter_dict, "linked_solution_type": "todo"})
        runtime_issues = await IssueService.issues.count_documents({**filter_dict, "linked_solution_type": "runtime_solution"})
        
        return {
            "total": total_issues,
            "open": open_issues,
            "in_progress": in_progress_issues,
            "resolved": resolved_issues,
            "resolution_rate": (resolved_issues / total_issues * 100) if total_issues > 0 else 0,
            "solution_types": {
                "rock": rock_issues,
                "todo": todo_issues,
                "runtime_solution": runtime_issues
            }
        }
