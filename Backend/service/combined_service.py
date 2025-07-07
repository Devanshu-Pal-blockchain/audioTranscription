from typing import List, Dict, Optional, Tuple
from uuid import UUID
from fastapi import HTTPException
from models.rock import Rock
from models.task import Task
from models.user import User
from .rock_service import RockService
from .task_service import TaskService
from .participants_service import UserService
from datetime import datetime

class CombinedService:
    """Service for handling operations across multiple collections"""

    @staticmethod
    async def get_quarter_rocks_tasks(
        quarter_id: UUID,
        include_comments: bool = False,
        include_users: bool = True
    ) -> List[Dict]:
        """Get all rocks and their tasks for a quarter"""
        rocks_with_tasks = []
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
        
        for rock in rocks:
            tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
            rock_dict = rock.model_dump()
            rock_dict["tasks"] = [task.model_dump() for task in tasks]
            
            if include_users and rock.assigned_to_id:
                user = await UserService.get_user(rock.assigned_to_id)
                if user:
                    rock_dict["assigned_user"] = {
                        "employee_id": str(user.employee_id),
                        "employee_name": user.employee_name,
                        "employee_email": user.employee_email,
                        "employee_role": user.employee_role
                    }
            
            rocks_with_tasks.append(rock_dict)
        
        return rocks_with_tasks

    @staticmethod
    async def get_quarter_rock(
        quarter_id: UUID,
        rock_id: UUID,
        include_comments: bool = False,
        include_users: bool = True
    ) -> Optional[Dict]:
        """Get a specific rock and its tasks from a quarter"""
        rock = await RockService.get_rock_by_quarter(quarter_id, rock_id)
        if not rock:
            return None
        
        tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
        rock_dict = rock.model_dump()
        rock_dict["tasks"] = [task.model_dump() for task in tasks]
        
        if include_users and rock.assigned_to_id:
            user = await UserService.get_user(rock.assigned_to_id)
            if user:
                rock_dict["assigned_user"] = {
                    "employee_id": str(user.employee_id),
                    "employee_name": user.employee_name,
                    "employee_email": user.employee_email,
                    "employee_role": user.employee_role
                }
        
        return rock_dict

    @staticmethod
    async def get_quarter_rock_task(
        quarter_id: UUID,
        rock_id: UUID,
        task_id: UUID,
        include_users: bool = True
    ) -> Optional[Dict]:
        """Get a specific rock and task from a quarter"""
        rock = await RockService.get_rock_by_quarter(quarter_id, rock_id)
        if not rock:
            return None
        
        task = await TaskService.get_task(task_id)
        if not task or task.rock_id != rock_id:
            return None
        
        result = {
            "rock": rock.model_dump(),
            "task": task.model_dump()
        }
        
        if include_users and rock.assigned_to_id:
            user = await UserService.get_user(rock.assigned_to_id)
            if user:
                result["assigned_user"] = {
                    "employee_id": str(user.employee_id),
                    "employee_name": user.employee_name,
                    "employee_email": user.employee_email,
                    "employee_role": user.employee_role
                }
        
        return result

    @staticmethod
    async def update_quarter_rock_task(
        quarter_id: UUID,
        rock_id: UUID,
        task_id: UUID,
        rock_update: Optional[Rock] = None,
        task_update: Optional[Task] = None
    ) -> Optional[Dict]:
        """Update a specific rock and/or task in a quarter"""
        # Verify rock belongs to quarter
        rock = await RockService.get_rock_by_quarter(quarter_id, rock_id)
        if not rock:
            return None
        
        # Update rock if provided
        if rock_update:
            rock = await RockService.update_rock(rock_id, rock_update)
            if not rock:
                return None
        
        # Update task if provided
        task = None
        if task_update:
            task = await TaskService.get_task(task_id)
            if not task or task.rock_id != rock_id:
                return None
            task = await TaskService.update_task(task_id, task_update)
        
        result = {
            "rock": rock.model_dump(),
            "task": task.model_dump() if task else None
        }
        
        if rock.assigned_to_id:
            user = await UserService.get_user(rock.assigned_to_id)
            if user:
                result["assigned_user"] = {
                    "employee_id": str(user.employee_id),
                    "employee_name": user.employee_name,
                    "employee_email": user.employee_email,
                    "employee_role": user.employee_role
                }
        
        return result

    @staticmethod
    async def delete_quarter_rock_task(
        quarter_id: UUID,
        rock_id: UUID,
        task_id: Optional[UUID] = None
    ) -> bool:
        """Delete a rock and/or specific task from a quarter"""
        # Verify rock belongs to quarter
        rock = await RockService.get_rock_by_quarter(quarter_id, rock_id)
        if not rock:
            return False
        
        if task_id:
            # Delete specific task
            task = await TaskService.get_task(task_id)
            if not task or task.rock_id != rock_id:
                return False
            return await TaskService.delete_task(task_id)
        else:
            # Delete rock and all its tasks
            return await CombinedService.delete_rock_and_tasks(quarter_id, rock_id)

    @staticmethod
    async def get_quarter_data(
        quarter_id: UUID,
        include_comments: bool = False,
        include_users: bool = True
    ) -> Dict:
        """Get all data for a quarter including rocks, tasks, and users (admin only)"""
        rocks_with_data = []
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
        
        for rock in rocks:
            rock_data = rock.model_dump()
            
            # Get tasks
            tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
            rock_data["tasks"] = [task.model_dump() for task in tasks]
            
            # Get assigned user
            if include_users and rock.assigned_to_id:
                user = await UserService.get_user(rock.assigned_to_id)
                if user:
                    rock_data["assigned_user"] = {
                        "employee_id": str(user.employee_id),
                        "employee_name": user.employee_name,
                        "employee_email": user.employee_email,
                        "employee_role": user.employee_role
                    }
            
            rocks_with_data.append(rock_data)
        
        return {
            "quarter_id": str(quarter_id),
            "rocks": rocks_with_data,
            "total_rocks": len(rocks_with_data)
        }

    @staticmethod
    async def get_rock_tasks(rock_id: UUID, include_comments: bool = False) -> Optional[Dict]:
        """Get a rock and all its tasks"""
        rock = await RockService.get_rock(rock_id)
        if not rock:
            return None
        
        tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
        rock_dict = rock.model_dump()
        rock_dict["tasks"] = [task.model_dump() for task in tasks]
        return rock_dict

    @staticmethod
    async def update_rock_and_tasks(
        quarter_id: UUID,
        rock_id: UUID,
        rock_update: Rock,
        tasks_update: List[Task]
    ) -> Optional[Dict]:
        """Update a rock and its tasks in a quarter"""
        # Verify rock belongs to quarter
        rock = await RockService.get_rock_by_quarter(quarter_id, rock_id)
        if not rock:
            raise HTTPException(status_code=404, detail="Rock not found in quarter")

        # Update rock
        updated_rock = await RockService.update_rock(rock_id, rock_update)
        if not updated_rock:
            return None

        # Update tasks
        updated_tasks = []
        for task in tasks_update:
            if task.rock_id != rock_id:
                continue
            updated_task = await TaskService.update_task(task.task_id, task)
            if updated_task:
                updated_tasks.append(updated_task)

        result = updated_rock.model_dump()
        result["tasks"] = [task.model_dump() for task in updated_tasks]
        return result

    @staticmethod
    async def create_rock_with_tasks(
        quarter_id: UUID,
        rock: Rock,
        tasks: List[Task]
    ) -> Dict:
        """Create a rock with its tasks in a quarter"""
        # Set quarter_id
        rock.quarter_id = quarter_id
        created_rock = await RockService.create_rock(rock)

        # Create tasks
        created_tasks = []
        for task in tasks:
            task.rock_id = created_rock.rock_id
            created_task = await TaskService.create_task(task)
            created_tasks.append(created_task)

        result = created_rock.model_dump()
        result["tasks"] = [task.model_dump() for task in created_tasks]
        return result

    @staticmethod
    async def delete_rock_and_tasks(quarter_id: UUID, rock_id: UUID) -> bool:
        """Delete a rock and all its tasks from a quarter"""
        # Verify rock belongs to quarter
        rock = await RockService.get_rock_by_quarter(quarter_id, rock_id)
        if not rock:
            return False

        # Get tasks to delete
        tasks = await TaskService.get_tasks_by_rock(rock_id)
        
        # Delete tasks first
        for task in tasks:
            await TaskService.delete_task(task.task_id)
        
        # Delete rock
        return await RockService.delete_rock(rock_id)

    @staticmethod
    async def update_rock_tasks(
        rock_id: UUID,
        tasks_update: List[Task]
    ) -> Optional[Dict]:
        """Update tasks for a specific rock"""
        rock = await RockService.get_rock(rock_id)
        if not rock:
            return None

        updated_tasks = []
        for task in tasks_update:
            if task.rock_id != rock_id:
                continue
            updated_task = await TaskService.update_task(task.task_id, task)
            if updated_task:
                updated_tasks.append(updated_task)

        result = rock.model_dump()
        result["tasks"] = [task.model_dump() for task in updated_tasks]
        return result

    @staticmethod
    async def create_rock_tasks(
        rock_id: UUID,
        tasks: List[Task]
    ) -> Optional[Dict]:
        """Create new tasks for a specific rock"""
        rock = await RockService.get_rock(rock_id)
        if not rock:
            return None

        created_tasks = []
        for task in tasks:
            task.rock_id = rock_id
            created_task = await TaskService.create_task(task)
            created_tasks.append(created_task)

        result = rock.model_dump()
        result["tasks"] = [task.model_dump() for task in created_tasks]
        return result

    @staticmethod
    async def delete_rock_tasks(rock_id: UUID) -> bool:
        """Delete all tasks for a specific rock"""
        rock = await RockService.get_rock(rock_id)
        if not rock:
            return False

        tasks = await TaskService.get_tasks_by_rock(rock_id)
        for task in tasks:
            await TaskService.delete_task(task.task_id)
        return True

    @staticmethod
    async def get_quarter_data_for_user(
        quarter_id: UUID,
        user_id: UUID,
        is_admin: bool,
        include_comments: bool = False
    ) -> Dict:
        """Get quarter data based on user role"""
        if is_admin:
            return await CombinedService.get_quarter_data(quarter_id, include_comments)
        
        # For regular users, only get their assigned rocks and tasks
        rocks_with_data = []
        rocks = await RockService.get_rocks_by_user(user_id)
        
        # Filter rocks by quarter
        for rock in rocks:
            if str(rock.quarter_id) != str(quarter_id):
                continue
                
            rock_data = rock.model_dump()
            tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
            rock_data["tasks"] = [task.model_dump() for task in tasks]
            
            # Get user profile
            user = await UserService.get_user(user_id)
            if user:
                rock_data["assigned_user"] = {
                    "employee_id": str(user.employee_id),
                    "employee_name": user.employee_name,
                    "employee_email": user.employee_email,
                    "employee_role": user.employee_role
                }
            
            rocks_with_data.append(rock_data)
        
        return {
            "quarter_id": str(quarter_id),
            "rocks": rocks_with_data,
            "total_rocks": len(rocks_with_data)
        }

    @staticmethod
    async def get_rock_data_for_user(
        rock_id: UUID,
        user_id: UUID,
        is_admin: bool,
        include_comments: bool = False
    ) -> Optional[Dict]:
        """Get rock data based on user role"""
        rock = await RockService.get_rock(rock_id)
        if not rock:
            return None
            
        if not is_admin and str(rock.assigned_to_id) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this rock"
            )
        
        return await CombinedService.get_rock_tasks(rock_id, include_comments)

    @staticmethod
    async def add_admin_comment(
        task_id: UUID,
        admin_id: UUID,
        content: str
    ) -> Optional[Task]:
        """Add an admin comment to a task"""
        # Verify admin user
        admin = await UserService.get_user(admin_id)
        if not admin or admin.employee_role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only admins can add comments"
            )
        
        comment = {
            "comment_id": str(UUID()),
            "commented_by": str(admin_id),
            "content": content,
            "created_at": datetime.utcnow(),
            "is_admin_comment": True
        }
        
        return await TaskService.add_comment(task_id, comment)

    @staticmethod
    async def update_admin_comment(
        task_id: UUID,
        comment_id: UUID,
        admin_id: UUID,
        content: str
    ) -> Optional[Task]:
        """Update an admin comment on a task"""
        # Verify admin user
        admin = await UserService.get_user(admin_id)
        if not admin or admin.employee_role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only admins can update comments"
            )
        
        task = await TaskService.get_task(task_id)
        if not task:
            return None
            
        # Verify comment exists and belongs to admin
        comment_exists = False
        for comment in task.comments:
            if str(comment.comment_id) == str(comment_id) and comment.is_admin_comment:
                comment_exists = True
                break
                
        if not comment_exists:
            raise HTTPException(
                status_code=404,
                detail="Admin comment not found"
            )
        
        return await TaskService.update_comment(task_id, comment_id, content)

    @staticmethod
    async def delete_admin_comment(
        task_id: UUID,
        comment_id: UUID,
        admin_id: UUID
    ) -> Optional[Task]:
        """Delete an admin comment from a task"""
        # Verify admin user
        admin = await UserService.get_user(admin_id)
        if not admin or admin.employee_role != "admin":
            raise HTTPException(
                status_code=403,
                detail="Only admins can delete comments"
            )
        
        task = await TaskService.get_task(task_id)
        if not task:
            return None
            
        # Verify comment exists and belongs to admin
        comment_exists = False
        for comment in task.comments:
            if str(comment.comment_id) == str(comment_id) and comment.is_admin_comment:
                comment_exists = True
                break
                
        if not comment_exists:
            raise HTTPException(
                status_code=404,
                detail="Admin comment not found"
            )
        
        return await TaskService.remove_comment(task_id, comment_id) 