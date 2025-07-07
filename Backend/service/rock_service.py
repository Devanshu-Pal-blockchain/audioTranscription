from typing import List, Optional, Dict, Tuple
from uuid import UUID
from fastapi import HTTPException
from models.rock import Rock
from models.task import Task
from .db import db
from .user_service import UserService
from .task_service import TaskService
from datetime import datetime

class RockService:
    collection = db.rocks

    @staticmethod
    async def create_rock(rock: Rock) -> Rock:
        """Create a new rock and update user's assigned rocks"""
        rock_dict = rock.model_dump()
        await RockService.collection.insert_one(rock_dict)
        
        # Update user's assigned rocks (two-way reference)
        if rock.assigned_to_id:
            await UserService.assign_rock(rock.assigned_to_id, rock.rock_id)
        
        return rock

    @staticmethod
    async def get_rock(rock_id: UUID) -> Optional[Rock]:
        """Get a rock by ID"""
        rock_dict = await RockService.collection.find_one({"rock_id": str(rock_id)})
        if not rock_dict:
            return None
        return Rock(**rock_dict)

    @staticmethod
    async def get_rock_by_quarter(quarter_id: UUID, rock_id: UUID) -> Optional[Rock]:
        """Get a specific rock in a quarter"""
        rock_dict = await RockService.collection.find_one({
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
        async for rock_dict in RockService.collection.find({"quarter_id": str(quarter_id)}):
            rocks.append(Rock(**rock_dict))
        return rocks

    @staticmethod
    async def get_rocks_with_tasks(quarter_id: UUID, include_comments: bool = False) -> List[Dict]:
        """Get all rocks for a quarter with their tasks"""
        rocks_with_tasks = []
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
        
        for rock in rocks:
            tasks = await TaskService.get_tasks_by_rock(rock.rock_id)
            rock_dict = rock.model_dump()
            
            if not include_comments:
                # Remove comments from tasks
                for task in tasks:
                    task.comments = []
            
            rock_dict["tasks"] = [task.model_dump() for task in tasks]
            rocks_with_tasks.append(rock_dict)
        
        return rocks_with_tasks

    @staticmethod
    async def get_rocks_by_user(user_id: UUID) -> List[Rock]:
        """Get all rocks assigned to a specific user"""
        rocks = []
        async for rock_dict in RockService.collection.find({"assigned_to_id": str(user_id)}):
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
        
        await RockService.collection.update_one(
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
    async def update_smart_objective(rock_id: UUID, smart_objective: str) -> Optional[Rock]:
        """Update a rock's SMART objective"""
        result = await RockService.collection.find_one_and_update(
            {"rock_id": str(rock_id)},
            {
                "$set": {
                    "smart_objective": smart_objective,
                    "updated_at": datetime.utcnow()
                }
            },
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

        result = await RockService.collection.delete_one({"rock_id": str(rock_id)})
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

        result = await RockService.collection.find_one_and_update(
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

        result = await RockService.collection.find_one_and_update(
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
        rock_id: UUID,
        rock_update: Rock,
        tasks_update: List[Task]
    ) -> Tuple[Optional[Rock], List[Task]]:
        """Update a rock and its tasks in a quarter"""
        # Verify rock belongs to quarter
        rock = await RockService.get_rock_by_quarter(quarter_id, rock_id)
        if not rock:
            return None, []

        # Update rock
        updated_rock = await RockService.update_rock(rock_id, rock_update)
        if not updated_rock:
            return None, []

        # Update tasks
        updated_tasks = []
        for task in tasks_update:
            if task.rock_id != rock_id:
                continue
            updated_task = await TaskService.update_task(task.task_id, task)
            if updated_task:
                updated_tasks.append(updated_task)

        return updated_rock, updated_tasks 