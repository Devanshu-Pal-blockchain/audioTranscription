from typing import List, Optional, Dict
from uuid import UUID
from fastapi import HTTPException
from models.issue import Issue
from .base_service import BaseService
from datetime import datetime
from utils.secure_fields import encrypt_dict, decrypt_dict, fill_required_fields

class IssueService(BaseService):
    EXCLUDE_FIELDS = ["id", "issue_id", "created_at", "updated_at", "raised_by_id", "quarter_id", "status", "raised_by"]
    EXCLUDE_TYPES = {
        "id": UUID,
        "issue_id": UUID,
        "raised_by_id": UUID,
        "quarter_id": UUID,
        "status": str,
        "raised_by": str,
        "created_at": datetime,
        "updated_at": datetime
    }

    @staticmethod
    def safe_decrypt_dict(doc):
        if not doc:
            return {}
        
        if "data_enc" in doc:
            data = decrypt_dict(doc, IssueService.EXCLUDE_FIELDS, IssueService.EXCLUDE_TYPES)
        else:
            data = doc.copy()
        
        # Handle required UUID fields that can't be None
        required_uuid_fields = ["id", "issue_id", "quarter_id"]
        for field in required_uuid_fields:
            if field not in data or data[field] is None or data[field] == "":
                import uuid
                data[field] = str(uuid.uuid4())
        
        # Handle optional UUID fields - convert empty strings to None
        optional_uuid_fields = ["raised_by_id"]
        for field in optional_uuid_fields:
            if field in data and data[field] == "":
                data[field] = None
        
        # Handle required datetime fields
        required_datetime_fields = ["created_at", "updated_at"]
        for field in required_datetime_fields:
            if field not in data or data[field] is None:
                from datetime import datetime
                data[field] = datetime.utcnow().isoformat()
        
        # Ensure required string fields have defaults
        if "issue_title" not in data or data["issue_title"] is None:
            data["issue_title"] = "Untitled Issue"
        if "description" not in data or data["description"] is None:
            data["description"] = ""
        if "raised_by" not in data or data["raised_by"] is None:
            data["raised_by"] = ""
        if "status" not in data or data["status"] is None:
            data["status"] = "open"
        
        return data

    @staticmethod
    async def create_issue(issue: Issue) -> Issue:
        quarter_dict = await IssueService.quarters.find_one({"id": str(issue.quarter_id)})
        if not quarter_dict:
            raise HTTPException(status_code=404, detail="Quarter not found")
        issue_dict = issue.model_dump()
        encrypted = encrypt_dict(issue_dict.copy(), IssueService.EXCLUDE_FIELDS)
        await IssueService.issues.insert_one(encrypted)
        return issue

    @staticmethod
    async def get_issue(issue_id: UUID) -> Optional[Issue]:
        doc = await IssueService.issues.find_one({"issue_id": str(issue_id)})
        if not doc:
            return None
        data = IssueService.safe_decrypt_dict(doc)
        return Issue(**data)

    @staticmethod
    async def get_issues_by_quarter(quarter_id: UUID) -> List[Issue]:
        issues = []
        async for doc in IssueService.issues.find({"quarter_id": str(quarter_id)}):
            data = IssueService.safe_decrypt_dict(doc)
            issues.append(Issue(**data))
        return issues

    @staticmethod
    async def get_issues_by_user(raised_by_id: UUID) -> List[Issue]:
        issues = []
        async for doc in IssueService.issues.find({"raised_by_id": str(raised_by_id)}):
            data = IssueService.safe_decrypt_dict(doc)
            issues.append(Issue(**data))
        return issues

    @staticmethod
    async def get_issues_by_status(status: str, quarter_id: Optional[UUID] = None) -> List[Issue]:
        filter_dict = {"status": status}
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        issues = []
        async for doc in IssueService.issues.find(filter_dict):
            data = IssueService.safe_decrypt_dict(doc)
            issues.append(Issue(**data))
        return issues

    @staticmethod
    async def get_issues_by_solution_type(solution_type: str, quarter_id: Optional[UUID] = None) -> List[Issue]:
        filter_dict = {"linked_solution_type": solution_type}
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        issues = []
        async for doc in IssueService.issues.find(filter_dict):
            data = IssueService.safe_decrypt_dict(doc)
            issues.append(Issue(**data))
        return issues

    @staticmethod
    async def update_issue(issue_id: UUID, update_data: Dict) -> Optional[Issue]:
        # First, get the existing issue to preserve all data
        existing_issue = await IssueService.get_issue(issue_id)
        if not existing_issue:
            return None
        
        # Convert existing issue to dict and merge with update data
        existing_data = existing_issue.model_dump()
        
        # Handle date serialization properly for any date fields
        for key, value in existing_data.items():
            if hasattr(value, "isoformat"):
                existing_data[key] = value.isoformat()
        
        existing_data.update(update_data)
        existing_data["updated_at"] = datetime.utcnow()
        
        # Re-encrypt the complete data
        encrypted = encrypt_dict(existing_data.copy(), IssueService.EXCLUDE_FIELDS)
        result = await IssueService.issues.update_one(
            {"issue_id": str(issue_id)},
            {"$set": encrypted}
        )
        if result.modified_count == 0:
            return None
        return await IssueService.get_issue(issue_id)

    @staticmethod
    async def delete_issue(issue_id: UUID) -> bool:
        result = await IssueService.issues.delete_one({"issue_id": str(issue_id)})
        return result.deleted_count > 0

    @staticmethod
    async def search_issues(query: str, quarter_id: Optional[UUID] = None) -> List[Issue]:
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
        async for doc in IssueService.issues.find(filter_dict):
            data = IssueService.safe_decrypt_dict(doc)
            issues.append(Issue(**data))
        return issues

    @staticmethod
    async def bulk_create_issues(issues: List[Issue]) -> List[Issue]:
        if not issues:
            return []
        encrypted_issues = [encrypt_dict(issue.model_dump().copy(), IssueService.EXCLUDE_FIELDS) for issue in issues]
        await IssueService.issues.insert_many(encrypted_issues)
        return issues

    @staticmethod
    async def get_issue_statistics(quarter_id: Optional[UUID] = None) -> Dict:
        filter_dict = {}
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        total_issues = await IssueService.issues.count_documents(filter_dict)
        open_issues = await IssueService.issues.count_documents({**filter_dict, "status": "open"})
        in_progress_issues = await IssueService.issues.count_documents({**filter_dict, "status": "in_progress"})
        resolved_issues = await IssueService.issues.count_documents({**filter_dict, "status": "resolved"})
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
