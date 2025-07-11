from typing import List, Optional, Dict
from uuid import UUID
from fastapi import HTTPException
from models.todo import Todo
from .base_service import BaseService
from datetime import datetime, date

class TodoService(BaseService):
    """Service for managing todos"""

    @staticmethod
    async def create_todo(todo: Todo) -> Todo:
        """Create a new todo"""
        # Validate quarter exists
        quarter_dict = await TodoService.quarters.find_one({"quarter_id": str(todo.quarter_id)})
        if not quarter_dict:
            raise HTTPException(status_code=404, detail="Quarter not found")
        
        todo_dict = todo.model_dump()
        await TodoService.todos.insert_one(todo_dict)
        return todo

    @staticmethod
    async def get_todo(todo_id: UUID) -> Optional[Todo]:
        """Get a todo by ID"""
        todo_dict = await TodoService.todos.find_one({"todo_id": str(todo_id)})
        if not todo_dict:
            return None
        return Todo(**todo_dict)

    @staticmethod
    async def get_todos_by_quarter(quarter_id: UUID) -> List[Todo]:
        """Get all todos for a specific quarter"""
        # Validate quarter exists
        quarter_dict = await TodoService.quarters.find_one({"quarter_id": str(quarter_id)})
        if not quarter_dict:
            raise HTTPException(status_code=404, detail="Quarter not found")

        todos = []
        async for todo_dict in TodoService.todos.find({"quarter_id": str(quarter_id)}):
            todos.append(Todo(**todo_dict))
        return todos

    @staticmethod
    async def get_todos_by_user(assigned_to_id: UUID) -> List[Todo]:
        """Get all todos assigned to a specific user"""
        todos = []
        async for todo_dict in TodoService.todos.find({"assigned_to_id": str(assigned_to_id)}):
            todos.append(Todo(**todo_dict))
        return todos

    @staticmethod
    async def get_todos_by_status(status: str, quarter_id: Optional[UUID] = None) -> List[Todo]:
        """Get todos by status, optionally filtered by quarter"""
        filter_dict = {"status": status}
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        
        todos = []
        async for todo_dict in TodoService.todos.find(filter_dict):
            todos.append(Todo(**todo_dict))
        return todos

    @staticmethod
    async def update_todo(todo_id: UUID, update_data: Dict) -> Optional[Todo]:
        """Update a todo"""
        # Remove fields that shouldn't be updated
        update_data.pop("id", None)
        update_data.pop("todo_id", None)
        update_data.pop("created_at", None)
        
        # Update timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await TodoService.todos.update_one(
            {"todo_id": str(todo_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            return None
        
        return await TodoService.get_todo(todo_id)

    @staticmethod
    async def delete_todo(todo_id: UUID) -> bool:
        """Delete a todo"""
        result = await TodoService.todos.delete_one({"todo_id": str(todo_id)})
        return result.deleted_count > 0

    @staticmethod
    async def get_overdue_todos() -> List[Todo]:
        """Get all overdue todos"""
        today = date.today()
        todos = []
        async for todo_dict in TodoService.todos.find({
            "due_date": {"$lt": today.isoformat()},
            "status": {"$ne": "completed"}
        }):
            todos.append(Todo(**todo_dict))
        return todos

    @staticmethod
    async def get_todos_due_soon(days: int = 7) -> List[Todo]:
        """Get todos due within specified days"""
        from datetime import timedelta
        target_date = date.today() + timedelta(days=days)
        
        todos = []
        async for todo_dict in TodoService.todos.find({
            "due_date": {"$lte": target_date.isoformat()},
            "status": {"$ne": "completed"}
        }):
            todos.append(Todo(**todo_dict))
        return todos

    @staticmethod
    async def bulk_create_todos(todos: List[Todo]) -> List[Todo]:
        """Create multiple todos at once"""
        if not todos:
            return []
        
        todo_dicts = [todo.model_dump() for todo in todos]
        await TodoService.todos.insert_many(todo_dicts)
        return todos

    @staticmethod
    async def get_todo_statistics(quarter_id: Optional[UUID] = None) -> Dict:
        """Get statistics about todos"""
        filter_dict = {}
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        
        total_todos = await TodoService.todos.count_documents(filter_dict)
        completed_todos = await TodoService.todos.count_documents({**filter_dict, "status": "completed"})
        pending_todos = await TodoService.todos.count_documents({**filter_dict, "status": "pending"})
        in_progress_todos = await TodoService.todos.count_documents({**filter_dict, "status": "in_progress"})
        
        today = date.today()
        overdue_todos = await TodoService.todos.count_documents({
            **filter_dict,
            "due_date": {"$lt": today.isoformat()},
            "status": {"$ne": "completed"}
        })
        
        return {
            "total": total_todos,
            "completed": completed_todos,
            "pending": pending_todos,
            "in_progress": in_progress_todos,
            "overdue": overdue_todos,
            "completion_rate": (completed_todos / total_todos * 100) if total_todos > 0 else 0
        }
