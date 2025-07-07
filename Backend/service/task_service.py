from typing import List, Optional, Dict, Tuple
from uuid import UUID
from fastapi import HTTPException
from models.task import Task, Comment
from .db import db
from .rock_service import RockService
from datetime import datetime

class TaskService:
    collection = db.tasks

    @staticmethod
    async def create_task(task: Task) -> Task:
        """Create a new task with rock validation"""
        # Validate rock exists
        rock = await RockService.get_rock(task.rock_id)
        if not rock:
            raise HTTPException(status_code=404, detail="Rock not found")
        
        task_dict = task.model_dump()
        await TaskService.collection.insert_one(task_dict)
        return task

    @staticmethod
    async def get_task(task_id: UUID) -> Optional[Task]:
        """Get a task by ID"""
        task_dict = await TaskService.collection.find_one({"task_id": str(task_id)})
        if not task_dict:
            return None
        return Task(**task_dict)

    @staticmethod
    async def get_tasks_by_rock(rock_id: UUID, include_comments: bool = True) -> List[Task]:
        """Get all tasks for a specific rock"""
        # Validate rock exists
        rock = await RockService.get_rock(rock_id)
        if not rock:
            raise HTTPException(status_code=404, detail="Rock not found")

        tasks = []
        async for task_dict in TaskService.collection.find({"rock_id": str(rock_id)}):
            task = Task(**task_dict)
            if not include_comments:
                task.comments = []
            tasks.append(task)
        return tasks

    @staticmethod
    async def get_tasks_by_week(rock_id: UUID, week: int) -> List[Task]:
        """Get all tasks for a specific rock and week"""
        # Validate rock exists
        rock = await RockService.get_rock(rock_id)
        if not rock:
            raise HTTPException(status_code=404, detail="Rock not found")

        tasks = []
        async for task_dict in TaskService.collection.find({
            "rock_id": str(rock_id),
            "week": week
        }):
            tasks.append(Task(**task_dict))
        return tasks

    @staticmethod
    async def create_task_for_week(rock_id: UUID, week: int, task: Task) -> Task:
        """Create a task for a specific week"""
        # Validate rock exists
        rock = await RockService.get_rock(rock_id)
        if not rock:
            raise HTTPException(status_code=404, detail="Rock not found")

        task.rock_id = rock_id
        task.week = week
        task_dict = task.model_dump()
        await TaskService.collection.insert_one(task_dict)
        return task

    @staticmethod
    async def update_task_for_week(task_id: UUID, week: int, task_update: Task) -> Optional[Task]:
        """Update a task for a specific week"""
        current_task = await TaskService.get_task(task_id)
        if not current_task:
            return None

        # Validate rock exists if changing rock_id
        if current_task.rock_id != task_update.rock_id:
            rock = await RockService.get_rock(task_update.rock_id)
            if not rock:
                raise HTTPException(status_code=404, detail="Rock not found")

        task_update.week = week
        update_data = task_update.model_dump(exclude={"id", "created_at"})
        update_data["updated_at"] = datetime.utcnow()
        
        await TaskService.collection.update_one(
            {"task_id": str(task_id)},
            {"$set": update_data}
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def delete_task_for_week(task_id: UUID, week: int) -> bool:
        """Delete a task for a specific week"""
        result = await TaskService.collection.delete_one({
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
            rock = await RockService.get_rock(task_update.rock_id)
            if not rock:
                raise HTTPException(status_code=404, detail="Rock not found")

        update_data = task_update.model_dump(exclude={"id", "created_at"})
        update_data["updated_at"] = datetime.utcnow()
        
        await TaskService.collection.update_one(
            {"task_id": str(task_id)},
            {"$set": update_data}
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def delete_task(task_id: UUID) -> bool:
        """Delete a task"""
        result = await TaskService.collection.delete_one({"task_id": str(task_id)})
        return result.deleted_count > 0

    @staticmethod
    async def add_subtask(task_id: UUID, subtask_key: str, subtask_content: str) -> Optional[Task]:
        """Add a subtask to a task"""
        await TaskService.collection.update_one(
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
        await TaskService.collection.update_one(
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
        await TaskService.collection.update_one(
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
        await TaskService.collection.update_one(
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
        await TaskService.collection.update_one(
            {
                "task_id": str(task_id),
                "comments.comment_id": str(comment_id)
            },
            {
                "$set": {
                    "comments.$.content": content,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return await TaskService.get_task(task_id)

    @staticmethod
    async def update_comment_by(task_id: UUID, comment_id: UUID, commented_by: str) -> Optional[Task]:
        """Update who commented on a task"""
        await TaskService.collection.update_one(
            {
                "task_id": str(task_id),
                "comments.comment_id": str(comment_id)
            },
            {
                "$set": {
                    "comments.$.commented_by": commented_by,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return await TaskService.get_task(task_id) 