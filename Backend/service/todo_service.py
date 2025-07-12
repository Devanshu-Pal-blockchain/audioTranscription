from typing import List, Optional, Dict
from uuid import UUID
from fastapi import HTTPException
from models.todo import Todo
from .base_service import BaseService
from datetime import datetime, date
from utils.secure_fields import encrypt_dict, decrypt_dict, fill_required_fields

class TodoService(BaseService):
    EXCLUDE_FIELDS = ["id", "todo_id", "created_at", "updated_at", "assigned_to_id", "status", "quarter_id"]
    EXCLUDE_TYPES = {
        "id": UUID,
        "todo_id": UUID,
        "assigned_to_id": UUID,
        "status": str,
        "quarter_id": UUID,
        "created_at": datetime,
        "updated_at": datetime
    }

    @staticmethod
    def safe_decrypt_dict(doc):
        if not doc:
            return {}
        
        if "data_enc" in doc:
            data = decrypt_dict(doc, TodoService.EXCLUDE_FIELDS, TodoService.EXCLUDE_TYPES)
        else:
            data = doc.copy()
        
        # Handle required UUID fields that can't be None
        required_uuid_fields = ["id", "todo_id", "quarter_id"]
        for field in required_uuid_fields:
            if field not in data or data[field] is None or data[field] == "":
                import uuid
                data[field] = str(uuid.uuid4())
        
        # Handle optional UUID fields - convert empty strings to None
        optional_uuid_fields = ["assigned_to_id"]
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
        if "task_title" not in data or data["task_title"] is None:
            data["task_title"] = "Untitled Task"
        if "assigned_to" not in data or data["assigned_to"] is None:
            data["assigned_to"] = ""
        if "designation" not in data or data["designation"] is None:
            data["designation"] = ""
        if "status" not in data or data["status"] is None:
            data["status"] = "pending"
        
        return data

    @staticmethod
    async def create_todo(todo: Todo) -> Todo:
        # Validate quarter exists
        quarter_dict = await TodoService.quarters.find_one({"id": str(todo.quarter_id)})
        if not quarter_dict:
            raise HTTPException(status_code=404, detail="Quarter not found")
        todo_dict = todo.model_dump()
        encrypted = encrypt_dict(todo_dict.copy(), TodoService.EXCLUDE_FIELDS)
        await TodoService.todos.insert_one(encrypted)
        return todo

    @staticmethod
    async def get_todo(todo_id: UUID) -> Optional[Todo]:
        doc = await TodoService.todos.find_one({"todo_id": str(todo_id)})
        if not doc:
            return None
        data = TodoService.safe_decrypt_dict(doc)
        return Todo(**data)

    @staticmethod
    async def get_todos_by_quarter(quarter_id: UUID) -> List[Todo]:
        todos = []
        async for doc in TodoService.todos.find({"quarter_id": str(quarter_id)}):
            data = TodoService.safe_decrypt_dict(doc)
            todos.append(Todo(**data))
        return todos

    @staticmethod
    async def get_todos_by_user(assigned_to_id: UUID) -> List[Todo]:
        todos = []
        async for doc in TodoService.todos.find({"assigned_to_id": str(assigned_to_id)}):
            data = TodoService.safe_decrypt_dict(doc)
            todos.append(Todo(**data))
        return todos

    @staticmethod
    async def get_todos_by_status(status: str, quarter_id: Optional[UUID] = None) -> List[Todo]:
        filter_dict = {"status": status}
        if quarter_id:
            filter_dict["quarter_id"] = str(quarter_id)
        todos = []
        async for doc in TodoService.todos.find(filter_dict):
            data = TodoService.safe_decrypt_dict(doc)
            todos.append(Todo(**data))
        return todos

    @staticmethod
    async def update_todo(todo_id: UUID, update_data: Dict) -> Optional[Todo]:
        update_data["updated_at"] = datetime.utcnow()
        encrypted = encrypt_dict(update_data.copy(), TodoService.EXCLUDE_FIELDS)
        result = await TodoService.todos.update_one(
            {"todo_id": str(todo_id)},
            {"$set": encrypted}
        )
        if result.modified_count == 0:
            return None
        return await TodoService.get_todo(todo_id)

    @staticmethod
    async def delete_todo(todo_id: UUID) -> bool:
        result = await TodoService.todos.delete_one({"todo_id": str(todo_id)})
        return result.deleted_count > 0

    @staticmethod
    async def get_overdue_todos() -> List[Todo]:
        today = date.today()
        todos = []
        async for doc in TodoService.todos.find({
            "due_date": {"$lt": today.isoformat()},
            "status": {"$ne": "completed"}
        }):
            data = TodoService.safe_decrypt_dict(doc)
            todos.append(Todo(**data))
        return todos

    @staticmethod
    async def get_todos_due_soon(days: int = 7) -> List[Todo]:
        from datetime import timedelta
        target_date = date.today() + timedelta(days=days)
        todos = []
        async for doc in TodoService.todos.find({
            "due_date": {"$lte": target_date.isoformat()},
            "status": {"$ne": "completed"}
        }):
            data = TodoService.safe_decrypt_dict(doc)
            todos.append(Todo(**data))
        return todos

    @staticmethod
    async def bulk_create_todos(todos: List[Todo]) -> List[Todo]:
        if not todos:
            return []
        encrypted_todos = [encrypt_dict(todo.model_dump().copy(), TodoService.EXCLUDE_FIELDS) for todo in todos]
        await TodoService.todos.insert_many(encrypted_todos)
        return todos

    @staticmethod
    async def get_todo_statistics(quarter_id: Optional[UUID] = None) -> Dict:
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
