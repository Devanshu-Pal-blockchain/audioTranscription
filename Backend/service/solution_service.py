from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from motor.motor_asyncio import AsyncIOMotorCollection
from models.solution import Solution, SolutionTimeline
from .db import get_database

class SolutionService:
    @staticmethod
    async def get_collection() -> AsyncIOMotorCollection:
        """Get the solutions collection"""
        db = await get_database()
        return db.solutions

    @staticmethod
    async def create_solution(solution_data: Dict[str, Any]) -> Solution:
        """Create a new solution"""
        collection = await SolutionService.get_collection()
        
        # Create solution instance
        solution = Solution(**solution_data)
        
        # Insert into database
        result = await collection.insert_one(solution.model_dump())
        
        if result.inserted_id:
            return solution
        else:
            raise Exception("Failed to create solution")

    @staticmethod
    async def get_solution(solution_id: UUID) -> Optional[Solution]:
        """Get a solution by ID"""
        collection = await SolutionService.get_collection()
        
        solution_data = await collection.find_one({"solution_id": solution_id})
        if solution_data:
            solution_data.pop("_id", None)
            return Solution(**solution_data)
        return None

    @staticmethod
    async def get_solutions_by_meeting(meeting_id: UUID) -> List[Solution]:
        """Get all solutions from a specific meeting"""
        collection = await SolutionService.get_collection()
        
        cursor = collection.find({"meeting_id": meeting_id})
        solutions = []
        
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions

    @staticmethod
    async def get_solutions_by_type(solution_type: str) -> List[Solution]:
        """Get all solutions by type (runtime, todo, rock)"""
        collection = await SolutionService.get_collection()
        
        cursor = collection.find({"solution_type": solution_type})
        solutions = []
        
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions

    @staticmethod
    async def get_solutions_by_owner(owner: str) -> List[Solution]:
        """Get all solutions assigned to a specific owner"""
        collection = await SolutionService.get_collection()
        
        cursor = collection.find({"owner": owner})
        solutions = []
        
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions

    @staticmethod
    async def get_solutions_by_status(status: str) -> List[Solution]:
        """Get all solutions by status"""
        collection = await SolutionService.get_collection()
        
        cursor = collection.find({"status": status})
        solutions = []
        
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions

    @staticmethod
    async def get_overdue_solutions() -> List[Solution]:
        """Get all overdue solutions"""
        collection = await SolutionService.get_collection()
        
        # Find solutions with end_date in the past and not completed/cancelled
        current_date = date.today()
        cursor = collection.find({
            "timeline.end_date": {"$lt": current_date},
            "status": {"$nin": ["completed", "cancelled"]}
        })
        
        solutions = []
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions

    @staticmethod
    async def get_solutions_by_parent_rock(parent_rock_id: UUID) -> List[Solution]:
        """Get all solutions (todos) related to a parent rock"""
        collection = await SolutionService.get_collection()
        
        cursor = collection.find({"parent_rock": parent_rock_id})
        solutions = []
        
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions

    @staticmethod
    async def get_solutions_by_issue(issue_id: UUID) -> List[Solution]:
        """Get all solutions that address a specific issue"""
        collection = await SolutionService.get_collection()
        
        cursor = collection.find({"issue_reference": issue_id})
        solutions = []
        
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions

    @staticmethod
    async def update_solution(solution_id: UUID, update_data: Dict[str, Any]) -> Optional[Solution]:
        """Update a solution"""
        collection = await SolutionService.get_collection()
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"solution_id": solution_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await SolutionService.get_solution(solution_id)
        return None

    @staticmethod
    async def update_solution_status(solution_id: UUID, status: str) -> Optional[Solution]:
        """Update solution status"""
        update_data = {"status": status}
        
        # Set timestamps based on status
        if status == "in_progress":
            update_data["started_at"] = datetime.utcnow()
        elif status == "completed":
            update_data["completed_at"] = datetime.utcnow()
            update_data["percentage_completion"] = 100
            
        return await SolutionService.update_solution(solution_id, update_data)

    @staticmethod
    async def update_progress(solution_id: UUID, percentage: int) -> Optional[Solution]:
        """Update solution progress percentage"""
        update_data = {"percentage_completion": max(0, min(100, percentage))}
        
        # Auto-update status based on progress
        if percentage == 100:
            update_data["status"] = "completed"
            update_data["completed_at"] = datetime.utcnow()
        elif percentage > 0:
            # Check current status and update if needed
            solution = await SolutionService.get_solution(solution_id)
            if solution and solution.status == "identified":
                update_data["status"] = "in_progress"
                update_data["started_at"] = datetime.utcnow()
        
        return await SolutionService.update_solution(solution_id, update_data)

    @staticmethod
    async def add_milestone(solution_id: UUID, milestone_id: UUID) -> Optional[Solution]:
        """Add a milestone to a solution"""
        collection = await SolutionService.get_collection()
        
        result = await collection.update_one(
            {"solution_id": solution_id},
            {
                "$addToSet": {"milestones": milestone_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await SolutionService.get_solution(solution_id)
        return None

    @staticmethod
    async def remove_milestone(solution_id: UUID, milestone_id: UUID) -> Optional[Solution]:
        """Remove a milestone from a solution"""
        collection = await SolutionService.get_collection()
        
        result = await collection.update_one(
            {"solution_id": solution_id},
            {
                "$pull": {"milestones": milestone_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await SolutionService.get_solution(solution_id)
        return None

    @staticmethod
    async def add_resource_required(solution_id: UUID, resource: str) -> Optional[Solution]:
        """Add a required resource to a solution"""
        collection = await SolutionService.get_collection()
        
        result = await collection.update_one(
            {"solution_id": solution_id},
            {
                "$addToSet": {"resources_required": resource},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await SolutionService.get_solution(solution_id)
        return None

    @staticmethod
    async def add_dependency(solution_id: UUID, dependency: str) -> Optional[Solution]:
        """Add a dependency to a solution"""
        collection = await SolutionService.get_collection()
        
        result = await collection.update_one(
            {"solution_id": solution_id},
            {
                "$addToSet": {"dependencies": dependency},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await SolutionService.get_solution(solution_id)
        return None

    @staticmethod
    async def delete_solution(solution_id: UUID) -> bool:
        """Delete a solution"""
        collection = await SolutionService.get_collection()
        
        result = await collection.delete_one({"solution_id": solution_id})
        return result.deleted_count > 0

    @staticmethod
    async def get_all_solutions() -> List[Solution]:
        """Get all solutions"""
        collection = await SolutionService.get_collection()
        
        cursor = collection.find({})
        solutions = []
        
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions

    @staticmethod
    async def search_solutions(search_term: str) -> List[Solution]:
        """Search solutions by title or description"""
        collection = await SolutionService.get_collection()
        
        # Case-insensitive search in title and description
        cursor = collection.find({
            "$or": [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}}
            ]
        })
        
        solutions = []
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions

    @staticmethod
    async def get_solution_statistics() -> Dict[str, Any]:
        """Get solution statistics"""
        collection = await SolutionService.get_collection()
        
        # Count by type
        types = ["runtime", "todo", "rock"]
        type_counts = {}
        for solution_type in types:
            type_counts[solution_type] = await collection.count_documents({"solution_type": solution_type})
        
        # Count by status
        statuses = ["identified", "assigned", "in_progress", "completed", "blocked", "cancelled", "deferred"]
        status_counts = {}
        for status in statuses:
            status_counts[status] = await collection.count_documents({"status": status})
        
        # Count overdue solutions
        current_date = date.today()
        overdue_count = await collection.count_documents({
            "timeline.end_date": {"$lt": current_date},
            "status": {"$nin": ["completed", "cancelled"]}
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
            "by_type": type_counts,
            "by_status": status_counts,
            "overdue": overdue_count,
            "average_completion": round(avg_completion, 2),
            "total": total_count
        }

    @staticmethod
    async def bulk_create_solutions(solutions_data: List[Dict[str, Any]]) -> List[Solution]:
        """Bulk create multiple solutions"""
        collection = await SolutionService.get_collection()
        
        # Create solution instances
        solutions = [Solution(**solution_data) for solution_data in solutions_data]
        
        # Bulk insert
        solution_dicts = [solution.model_dump() for solution in solutions]
        result = await collection.insert_many(solution_dicts)
        
        if result.inserted_ids:
            return solutions
        else:
            raise Exception("Failed to create solutions")

    @staticmethod
    async def bulk_update_status(solution_ids: List[UUID], status: str) -> int:
        """Bulk update status for multiple solutions"""
        collection = await SolutionService.get_collection()
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        # Add appropriate timestamps based on status
        if status == "in_progress":
            update_data["started_at"] = datetime.utcnow()
        elif status == "completed":
            update_data["completed_at"] = datetime.utcnow()
            update_data["percentage_completion"] = 100
        
        result = await collection.update_many(
            {"solution_id": {"$in": solution_ids}},
            {"$set": update_data}
        )
        
        return result.modified_count

    @staticmethod
    async def get_solutions_due_soon(days: int = 7) -> List[Solution]:
        """Get solutions due within specified number of days"""
        collection = await SolutionService.get_collection()
        
        from datetime import timedelta
        target_date = date.today() + timedelta(days=days)
        
        cursor = collection.find({
            "timeline.end_date": {"$lte": target_date, "$gte": date.today()},
            "status": {"$nin": ["completed", "cancelled"]}
        })
        
        solutions = []
        async for solution_data in cursor:
            solution_data.pop("_id", None)
            solutions.append(Solution(**solution_data))
            
        return solutions
