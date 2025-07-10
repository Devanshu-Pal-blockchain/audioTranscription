from typing import List, Optional, Dict, Tuple
from uuid import UUID
from fastapi import HTTPException
from models.rock import Rock
from models.task import Task
from .base_service import BaseService
from .user_service import UserService
from datetime import datetime

class RockService(BaseService):
    """Service for managing rocks"""

    @staticmethod
    async def create_rock(rock: Rock) -> Rock:
        """Create a new rock and update user's assigned rocks"""
        rock_dict = rock.model_dump()
        await RockService.rocks.insert_one(rock_dict)
        
        # Update user's assigned rocks (two-way reference)
        if rock.assigned_to_id:
            await UserService.assign_rock(rock.assigned_to_id, rock.rock_id)
        
        return rock

    @staticmethod
    async def get_rock(rock_id: UUID) -> Optional[Rock]:
        """Get a rock by ID"""
        rock_dict = await RockService.rocks.find_one({"rock_id": str(rock_id)})
        if not rock_dict:
            return None
        return Rock(**rock_dict)

    @staticmethod
    async def get_rock_by_quarter(quarter_id: UUID, rock_id: UUID) -> Optional[Rock]:
        """Get a specific rock in a quarter"""
        rock_dict = await RockService.rocks.find_one({
            "quarter_id": str(quarter_id),
            "rock_id": str(rock_id)
        })
        if not rock_dict:
            return None
        return Rock(**rock_dict)

    @staticmethod
    async def get_rocks_by_quarter(quarter_id: UUID) -> List[Rock]:
        """Get all rocks for a specific quarter"""
        rocks = []
        async for rock_dict in RockService.rocks.find({"quarter_id": str(quarter_id)}):
            rocks.append(Rock(**rock_dict))
        return rocks

    @staticmethod
    async def get_rocks_with_tasks(quarter_id: UUID, include_comments: bool = False) -> List[Dict]:
        """Get all rocks for a quarter with their tasks"""
        rocks_with_tasks = []
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
        
        for rock in rocks:
            # Get tasks directly from tasks collection
            tasks = []
            async for task_dict in RockService.tasks.find({"rock_id": str(rock.rock_id)}):
                task = Task(**task_dict)
                if not include_comments:
                    task.comments = []
                tasks.append(task)
            
            rock_dict = rock.model_dump()
            rock_dict["tasks"] = [task.model_dump() for task in tasks]
            rocks_with_tasks.append(rock_dict)
        
        return rocks_with_tasks

    @staticmethod
    async def get_rocks_by_user(user_id: UUID) -> List[Rock]:
        """Get all rocks assigned to a specific user"""
        rocks = []
        async for rock_dict in RockService.rocks.find({"assigned_to_id": str(user_id)}):
            rocks.append(Rock(**rock_dict))
        return rocks

    @staticmethod
    async def update_rock(rock_id: UUID, rock_update: Rock) -> Optional[Rock]:
        """Update a rock and maintain two-way references"""
        # Get current rock to check for assignment changes
        current_rock = await RockService.get_rock(rock_id)
        if not current_rock:
            return None

        update_data = rock_update.model_dump(exclude={"id", "created_at"})
        update_data["updated_at"] = datetime.utcnow()
        
        await RockService.rocks.update_one(
            {"rock_id": str(rock_id)},
            {"$set": update_data}
        )

        # Handle assignment changes (two-way reference)
        if current_rock.assigned_to_id != rock_update.assigned_to_id:
            # Remove rock from previous assignee
            if current_rock.assigned_to_id:
                await UserService.unassign_rock(current_rock.assigned_to_id, rock_id)
            # Add rock to new assignee
            if rock_update.assigned_to_id:
                await UserService.assign_rock(rock_update.assigned_to_id, rock_id)

        return await RockService.get_rock(rock_id)

    @staticmethod
    async def update_completion_status(rock_id: UUID, status: str, percentage_completion: Optional[int] = None) -> Optional[Rock]:
        """Update a rock's completion status and optionally percentage"""
        update_data = {
            "status": status,
            "updated_at": datetime.utcnow()
        }
        
        # Set percentage based on status if not provided
        if percentage_completion is not None:
            update_data["percentage_completion"] = percentage_completion
        elif status == "completed":
            update_data["percentage_completion"] = 100
        elif status == "not_started":
            update_data["percentage_completion"] = 0
            
        result = await RockService.rocks.find_one_and_update(
            {"rock_id": str(rock_id)},
            {"$set": update_data},
            return_document=True
        )
        return Rock(**result) if result else None

    @staticmethod
    async def delete_rock(rock_id: UUID) -> bool:
        """Delete a rock and clean up user references"""
        # Get rock to clean up references
        rock = await RockService.get_rock(rock_id)
        if rock and rock.assigned_to_id:
            # Remove rock from user's assigned rocks
            await UserService.unassign_rock(rock.assigned_to_id, rock_id)

        result = await RockService.rocks.delete_one({"rock_id": str(rock_id)})
        return result.deleted_count > 0

    @staticmethod
    async def assign_rock(rock_id: UUID, user_id: UUID, user_name: str) -> Optional[Rock]:
        """Assign a rock to a user"""
        # Check if rock is already assigned
        rock = await RockService.get_rock(rock_id)
        if rock and rock.assigned_to_id:
            raise HTTPException(
                status_code=400,
                detail="Rock is already assigned to a user"
            )

        result = await RockService.rocks.find_one_and_update(
            {"rock_id": str(rock_id)},
            {
                "$set": {
                    "assigned_to_id": str(user_id),
                    "assigned_to_name": user_name,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        
        if result:
            # Update user's assigned rocks
            await UserService.assign_rock(user_id, rock_id)
            return Rock(**result)
        return None

    @staticmethod
    async def unassign_rock(rock_id: UUID) -> Optional[Rock]:
        """Remove assignment from a rock"""
        # Get current assignment to clean up user reference
        rock = await RockService.get_rock(rock_id)
        if rock and rock.assigned_to_id:
            await UserService.unassign_rock(rock.assigned_to_id, rock_id)

        result = await RockService.rocks.find_one_and_update(
            {"rock_id": str(rock_id)},
            {
                "$unset": {
                    "assigned_to_id": "",
                    "assigned_to_name": ""
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        return Rock(**result) if result else None

    @staticmethod
    async def get_assignment_info(rock_id: UUID) -> Optional[Dict[str, str]]:
        """Get assignment information for a rock"""
        rock = await RockService.get_rock(rock_id)
        if not rock or not rock.assigned_to_id:
            return None
        return {
            "assigned_to_id": str(rock.assigned_to_id),
            "assigned_to_name": rock.assigned_to_name
        }

    @staticmethod
    async def update_rock_and_tasks(
        quarter_id: UUID,
        rock_update: Rock,
        tasks_update: List[Task]
    ) -> Tuple[Optional[Rock], List[Task]]:
        """Update a rock and its tasks atomically"""
        # Validate rock exists in quarter
        current_rock = await RockService.get_rock_by_quarter(quarter_id, rock_update.rock_id)
        if not current_rock:
            return None, []

        # Update rock
        updated_rock = await RockService.update_rock(rock_update.rock_id, rock_update)
        if not updated_rock:
            return None, []

        # Update tasks
        updated_tasks = []
        for task in tasks_update:
            task_dict = task.model_dump()
            task_dict["rock_id"] = str(rock_update.rock_id)
            task_dict["updated_at"] = datetime.utcnow()
            
            await RockService.tasks.update_one(
                {"task_id": str(task.task_id)},
                {"$set": task_dict},
                upsert=True
            )
            updated_tasks.append(task)

        return updated_rock, updated_tasks 