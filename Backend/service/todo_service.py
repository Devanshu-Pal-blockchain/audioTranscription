from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorCollection
from models.todo import ToDo
from .db import get_database

class ToDoService:
    @staticmethod
    async def get_collection() -> AsyncIOMotorCollection:
        """Get the todos collection"""
        db = await get_database()
        return db.todos

    @staticmethod
    async def create_todo(todo_data: Dict[str, Any]) -> ToDo:
        """Create a new todo"""
        collection = await ToDoService.get_collection()
        
        # Create todo instance
        todo = ToDo(**todo_data)
        
        # Insert into database
        result = await collection.insert_one(todo.model_dump())
        
        if result.inserted_id:
            return todo
        else:
            raise Exception("Failed to create todo")

    @staticmethod
    async def get_todo(todo_id: UUID) -> Optional[ToDo]:
        """Get a todo by ID"""
        collection = await ToDoService.get_collection()
        
        todo_data = await collection.find_one({"todo_id": todo_id})
        if todo_data:
            todo_data.pop("_id", None)
            return ToDo(**todo_data)
        return None

    @staticmethod
    async def get_todos_by_meeting(meeting_id: UUID) -> List[ToDo]:
        """Get all todos from a specific meeting"""
        collection = await ToDoService.get_collection()
        
        cursor = collection.find({"meeting_id": meeting_id})
        todos = []
        
        async for todo_data in cursor:
            todo_data.pop("_id", None)
            todos.append(ToDo(**todo_data))
            
        return todos

    @staticmethod
    async def get_todos_by_owner(owner_id: UUID) -> List[ToDo]:
        """Get all todos assigned to a specific owner"""
        collection = await ToDoService.get_collection()
        
        cursor = collection.find({"owner_id": owner_id})
        todos = []
        
        async for todo_data in cursor:
            todo_data.pop("_id", None)
            todos.append(ToDo(**todo_data))
            
        return todos

    @staticmethod
    async def get_todos_by_status(status: str) -> List[ToDo]:
        """Get all todos by status"""
        collection = await ToDoService.get_collection()
        
        cursor = collection.find({"status": status})
        todos = []
        
        async for todo_data in cursor:
            todo_data.pop("_id", None)
            todos.append(ToDo(**todo_data))
            
        return todos

    @staticmethod
    async def get_todos_by_parent_rock(parent_rock_id: UUID) -> List[ToDo]:
        """Get all todos associated with a parent rock"""
        collection = await ToDoService.get_collection()
        
        cursor = collection.find({"parent_rock_id": parent_rock_id})
        todos = []
        
        async for todo_data in cursor:
            todo_data.pop("_id", None)
            todos.append(ToDo(**todo_data))
            
        return todos

    @staticmethod
    async def get_overdue_todos() -> List[ToDo]:
        """Get all overdue todos"""
        collection = await ToDoService.get_collection()
        
        current_time = datetime.utcnow()
        cursor = collection.find({
            "deadline": {"$lt": current_time},
            "status": {"$ne": "completed"}
        })
        
        todos = []
        async for todo_data in cursor:
            todo_data.pop("_id", None)
            todos.append(ToDo(**todo_data))
            
        return todos

    @staticmethod
    async def get_due_soon_todos(days: int = 3) -> List[ToDo]:
        """Get todos due within specified days"""
        collection = await ToDoService.get_collection()
        
        future_date = datetime.utcnow() + timedelta(days=days)
        cursor = collection.find({
            "deadline": {"$lte": future_date},
            "status": {"$ne": "completed"}
        })
        
        todos = []
        async for todo_data in cursor:
            todo_data.pop("_id", None)
            todos.append(ToDo(**todo_data))
            
        return todos

    @staticmethod
    async def update_todo(todo_id: UUID, update_data: Dict[str, Any]) -> Optional[ToDo]:
        """Update a todo"""
        collection = await ToDoService.get_collection()
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        # Set completion date if marking as completed
        if update_data.get("status") == "completed":
            update_data["completed_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"todo_id": todo_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await ToDoService.get_todo(todo_id)
        return None

    @staticmethod
    async def update_todo_status(todo_id: UUID, status: str) -> Optional[ToDo]:
        """Update todo status"""
        update_data = {"status": status}
        return await ToDoService.update_todo(todo_id, update_data)

    @staticmethod
    async def mark_todo_completed(todo_id: UUID) -> Optional[ToDo]:
        """Mark todo as completed"""
        return await ToDoService.update_todo_status(todo_id, "completed")

    @staticmethod
    async def delete_todo(todo_id: UUID) -> bool:
        """Delete a todo"""
        collection = await ToDoService.get_collection()
        
        result = await collection.delete_one({"todo_id": todo_id})
        return result.deleted_count > 0

    @staticmethod
    async def get_all_todos() -> List[ToDo]:
        """Get all todos"""
        collection = await ToDoService.get_collection()
        
        cursor = collection.find({})
        todos = []
        
        async for todo_data in cursor:
            todo_data.pop("_id", None)
            todos.append(ToDo(**todo_data))
            
        return todos

    @staticmethod
    async def search_todos(search_term: str) -> List[ToDo]:
        """Search todos by title or description"""
        collection = await ToDoService.get_collection()
        
        # Case-insensitive search in title and description
        cursor = collection.find({
            "$or": [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"description": {"$regex": search_term, "$options": "i"}}
            ]
        })
        
        todos = []
        async for todo_data in cursor:
            todo_data.pop("_id", None)
            todos.append(ToDo(**todo_data))
            
        return todos

    @staticmethod
    async def get_todo_statistics() -> Dict[str, Any]:
        """Get todo statistics"""
        collection = await ToDoService.get_collection()
        
        # Count by status
        status_counts = {
            "pending": await collection.count_documents({"status": "pending"}),
            "in_progress": await collection.count_documents({"status": "in_progress"}),
            "completed": await collection.count_documents({"status": "completed"})
        }
        
        # Count overdue todos
        current_time = datetime.utcnow()
        overdue_count = await collection.count_documents({
            "deadline": {"$lt": current_time},
            "status": {"$ne": "completed"}
        })
        
        # Count due soon (next 3 days)
        future_date = current_time + timedelta(days=3)
        due_soon_count = await collection.count_documents({
            "deadline": {"$lte": future_date},
            "status": {"$ne": "completed"}
        })
        
        # Total count
        total_count = await collection.count_documents({})
        
        # Count by meeting type
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
            "due_soon": due_soon_count,
            "total": total_count
        }

    @staticmethod
    async def bulk_create_todos(todos_data: List[Dict[str, Any]]) -> List[ToDo]:
        """Bulk create multiple todos"""
        collection = await ToDoService.get_collection()
        
        # Create todo instances
        todos = [ToDo(**todo_data) for todo_data in todos_data]
        
        # Bulk insert
        todo_dicts = [todo.model_dump() for todo in todos]
        result = await collection.insert_many(todo_dicts)
        
        if result.inserted_ids:
            return todos
        else:
            raise Exception("Failed to create todos")

    @staticmethod
    async def bulk_update_status(todo_ids: List[UUID], status: str) -> int:
        """Bulk update status for multiple todos"""
        collection = await ToDoService.get_collection()
        
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        # Add completed_at if marking as completed
        if status == "completed":
            update_data["completed_at"] = datetime.utcnow()
        
        result = await collection.update_many(
            {"todo_id": {"$in": todo_ids}},
            {"$set": update_data}
        )
        
        return result.modified_count

    @staticmethod
    async def get_completion_rate_by_owner(owner_id: UUID) -> Dict[str, Any]:
        """Get completion rate statistics for a specific owner"""
        collection = await ToDoService.get_collection()
        
        total_todos = await collection.count_documents({"owner_id": owner_id})
        completed_todos = await collection.count_documents({
            "owner_id": owner_id,
            "status": "completed"
        })
        
        completion_rate = (completed_todos / total_todos * 100) if total_todos > 0 else 0
        
        return {
            "owner_id": str(owner_id),
            "total_todos": total_todos,
            "completed_todos": completed_todos,
            "completion_rate": round(completion_rate, 2)
        }

    @staticmethod
    async def validate_timeframe(deadline: datetime) -> bool:
        """Validate that todo deadline is within 1-14 days"""
        current_time = datetime.utcnow()
        min_deadline = current_time + timedelta(days=1)
        max_deadline = current_time + timedelta(days=14)
        
        return min_deadline <= deadline <= max_deadline
