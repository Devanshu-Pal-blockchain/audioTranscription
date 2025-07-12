from typing import List, Optional, Dict, Tuple
from uuid import UUID
from fastapi import HTTPException
from models.task import Task, Comment
from models.rock import Rock
from .base_service import BaseService
from datetime import datetime
from utils.secure_fields import encrypt_dict, decrypt_dict, fill_required_fields

class TaskService(BaseService):
    EXCLUDE_FIELDS = ["id", "task_id", "rock_id", "created_at", "updated_at"]
    EXCLUDE_TYPES = {
        "id": UUID,
        "task_id": UUID,
        "rock_id": UUID,
        "created_at": datetime,
        "updated_at": datetime
    }

    @staticmethod
    def safe_decrypt_dict(doc):
        if not doc:
            return {}
        
        if "data_enc" in doc:
            data = decrypt_dict(doc, TaskService.EXCLUDE_FIELDS, TaskService.EXCLUDE_TYPES)
        else:
            data = doc.copy()
        
        # Handle required UUID fields that can't be None
        required_uuid_fields = ["id", "task_id", "rock_id"]
        for field in required_uuid_fields:
            if field not in data or data[field] is None or data[field] == "":
                import uuid
                data[field] = str(uuid.uuid4())
        
        # Handle required datetime fields
        required_datetime_fields = ["created_at", "updated_at"]
        for field in required_datetime_fields:
            if field not in data or data[field] is None:
                from datetime import datetime
                data[field] = datetime.utcnow().isoformat()
        
        # Ensure required fields have defaults
        if "task" not in data or data["task"] is None:
            data["task"] = "Untitled Task"
        if "week" not in data or data["week"] is None:
            data["week"] = 1
        if "comments" not in data or data["comments"] is None:
            data["comments"] = []
        
        return data

    @staticmethod
    async def create_task(task: Task) -> Task:
        """Create a new task with rock validation"""
        # Validate rock exists
        rock_dict = await TaskService.rocks.find_one({"rock_id": str(task.rock_id)})
        if not rock_dict:
            raise HTTPException(status_code=404, detail="Rock not found")
        
        task_dict = task.model_dump()
        encrypted = encrypt_dict(task_dict.copy(), TaskService.EXCLUDE_FIELDS)
        await TaskService.tasks.insert_one(encrypted)
        return task

    @staticmethod
    async def get_task(task_id: UUID) -> Optional[Task]:
        """Get a task by ID"""
        task_dict = await TaskService.tasks.find_one({"task_id": str(task_id)})
        if not task_dict:
            return None
        data = TaskService.safe_decrypt_dict(task_dict)
        return Task(**data)

    @staticmethod
    async def get_tasks_by_rock(rock_id: UUID, include_comments: bool = True) -> List[Task]:
        """Get all tasks for a specific rock"""
        # Validate rock exists
        rock_dict = await TaskService.rocks.find_one({"rock_id": str(rock_id)})
        if not rock_dict:
            raise HTTPException(status_code=404, detail="Rock not found")

        tasks = []
        async for doc in TaskService.tasks.find({"rock_id": str(rock_id)}):
            data = TaskService.safe_decrypt_dict(doc)
            task = Task(**data)
            if not include_comments:
                task.comments = []
            tasks.append(task)
        return tasks

    @staticmethod
    async def get_tasks_by_week(rock_id: UUID, week: int) -> List[Task]:
        """Get all tasks for a specific rock and week"""
        # Validate rock exists
        rock_dict = await TaskService.rocks.find_one({"rock_id": str(rock_id)})
        if not rock_dict:
            raise HTTPException(status_code=404, detail="Rock not found")

        tasks = []
        async for doc in TaskService.tasks.find({
            "rock_id": str(rock_id),
            "week": week
        }):
            data = TaskService.safe_decrypt_dict(doc)
            tasks.append(Task(**data))
        return tasks

    @staticmethod
    async def create_task_for_week(rock_id: UUID, week: int, task: Task) -> Task:
        """Create a task for a specific week"""
        # Validate rock exists
        rock_dict = await TaskService.rocks.find_one({"rock_id": str(rock_id)})
        if not rock_dict:
            raise HTTPException(status_code=404, detail="Rock not found")

        task.rock_id = rock_id
        task.week = week
        task_dict = task.model_dump()
        encrypted = encrypt_dict(task_dict.copy(), TaskService.EXCLUDE_FIELDS)
        await TaskService.tasks.insert_one(encrypted)
        return task

    @staticmethod
    async def update_task_for_week(task_id: UUID, week: int, task_update: Task) -> Optional[Task]:
        """Update a task for a specific week"""
        current_task = await TaskService.get_task(task_id)
        if not current_task:
            return None

        # Validate rock exists if changing rock_id
        if current_task.rock_id != task_update.rock_id:
            rock_dict = await TaskService.rocks.find_one({"rock_id": str(task_update.rock_id)})
            if not rock_dict:
                raise HTTPException(status_code=404, detail="Rock not found")

        task_update.week = week
        update_data = task_update.model_dump(exclude={"id", "created_at"})
        update_data["updated_at"] = datetime.utcnow()
        encrypted = encrypt_dict(update_data.copy(), TaskService.EXCLUDE_FIELDS)
        
        await TaskService.tasks.update_one(
            {"task_id": str(task_id)},
            {"$set": encrypted}
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def delete_task_for_week(task_id: UUID, week: int) -> bool:
        """Delete a task for a specific week"""
        result = await TaskService.tasks.delete_one({
            "task_id": str(task_id),
            "week": week
        })
        return result.deleted_count > 0

    @staticmethod
    async def update_task(task_id: UUID, task_update: Task) -> Optional[Task]:
        """Update a task with rock validation"""
        # Validate task exists
        current_task = await TaskService.get_task(task_id)
        if not current_task:
            return None

        # If rock_id is changing, validate new rock exists
        if current_task.rock_id != task_update.rock_id:
            rock_dict = await TaskService.rocks.find_one({"rock_id": str(task_update.rock_id)})
            if not rock_dict:
                raise HTTPException(status_code=404, detail="Rock not found")

        update_data = task_update.model_dump(exclude={"id", "created_at"})
        update_data["updated_at"] = datetime.utcnow()
        encrypted = encrypt_dict(update_data.copy(), TaskService.EXCLUDE_FIELDS)
        
        await TaskService.tasks.update_one(
            {"task_id": str(task_id)},
            {"$set": encrypted}
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def delete_task(task_id: UUID) -> bool:
        """Delete a task"""
        result = await TaskService.tasks.delete_one({"task_id": str(task_id)})
        return result.deleted_count > 0

    @staticmethod
    async def add_subtask(task_id: UUID, subtask_key: str, subtask_content: str) -> Optional[Task]:
        """Add a subtask to a task"""
        await TaskService.tasks.update_one(
            {"task_id": str(task_id)},
            {
                "$set": {
                    f"sub_tasks.{subtask_key}": subtask_content,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def remove_subtask(task_id: UUID, subtask_key: str) -> Optional[Task]:
        """Remove a subtask from a task"""
        await TaskService.tasks.update_one(
            {"task_id": str(task_id)},
            {
                "$unset": {
                    f"sub_tasks.{subtask_key}": ""
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def add_comment(task_id: UUID, comment: Comment) -> Optional[Task]:
        """Add a comment to a task"""
        comment_dict = comment.model_dump()
        await TaskService.tasks.update_one(
            {"task_id": str(task_id)},
            {
                "$push": {
                    "comments": comment_dict
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def remove_comment(task_id: UUID, comment_id: UUID) -> Optional[Task]:
        """Remove a comment from a task"""
        await TaskService.tasks.update_one(
            {"task_id": str(task_id)},
            {
                "$pull": {
                    "comments": {
                        "comment_id": str(comment_id)
                    }
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def update_comment(task_id: UUID, comment_id: UUID, content: str) -> Optional[Task]:
        """Update a comment's content"""
        await TaskService.tasks.update_one(
            {
                "task_id": str(task_id),
                "comments.comment_id": str(comment_id)
            },
            {
                "$set": {
                    "comments.$.content": content,
                    "comments.$.updated_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def update_comment_by(task_id: UUID, comment_id: UUID, commented_by: str) -> Optional[Task]:
        """Update a comment's author"""
        await TaskService.tasks.update_one(
            {
                "task_id": str(task_id),
                "comments.comment_id": str(comment_id)
            },
            {
                "$set": {
                    "comments.$.commented_by": commented_by,
                    "comments.$.updated_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return await TaskService.get_task(task_id) 