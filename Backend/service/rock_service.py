from typing import List, Optional, Dict, Tuple
from uuid import UUID
from fastapi import HTTPException
from models.rock import Rock
from models.task import Task
from .base_service import BaseService
from .user_service import UserService
from datetime import datetime
from utils.secure_fields import encrypt_dict, decrypt_dict, fill_required_fields
from models.rock import RockPayload

class RockService(BaseService):
    EXCLUDE_FIELDS = ["id", "rock_id", "created_at", "updated_at", "assigned_to_id", "quarter_id", "assigned_to_name"]
    EXCLUDE_TYPES = {
        "id": UUID,
        "rock_id": UUID,
        "assigned_to_id": UUID,
        "quarter_id": UUID,
        "created_at": datetime,
        "updated_at": datetime,
        "assigned_to_name": str
    }

    @staticmethod
    def safe_decrypt_dict(doc):
        print("DEBUG: Original DB doc for Rock:", doc)
        if not doc:
            return {}
        
        if "data_enc" in doc:
            data = decrypt_dict(doc, RockService.EXCLUDE_FIELDS, RockService.EXCLUDE_TYPES)
        else:
            data = doc.copy()
        
        print("DEBUG: Decrypted data for Rock:", data)
        
        # Handle required UUID fields that can't be None
        required_uuid_fields = ["id", "rock_id", "quarter_id"]
        for field in required_uuid_fields:
            if field not in data or data[field] is None or data[field] == "":
                # Generate new UUID for missing required fields
                import uuid
                data[field] = str(uuid.uuid4())
                print(f"DEBUG: Generated new UUID for missing required field '{field}': {data[field]}")
        
        # Handle optional UUID fields - convert empty strings to None
        optional_uuid_fields = ["assigned_to_id"]
        for field in optional_uuid_fields:
            if field in data and data[field] == "":
                data[field] = None
                print(f"DEBUG: Converted empty string to None for optional UUID field '{field}'")
        
        # Handle required datetime fields
        required_datetime_fields = ["created_at", "updated_at"]
        for field in required_datetime_fields:
            if field not in data or data[field] is None:
                from datetime import datetime
                data[field] = datetime.utcnow().isoformat()
                print(f"DEBUG: Generated new datetime for missing required field '{field}': {data[field]}")
        
        # Ensure required string fields have defaults
        if "rock_name" not in data or data["rock_name"] is None:
            data["rock_name"] = "Untitled Rock"
        if "smart_objective" not in data or data["smart_objective"] is None:
            data["smart_objective"] = data["rock_name"]
        
        # Ensure assigned_to_name is a string
        if data.get("assigned_to_name") is None:
            data["assigned_to_name"] = ""
            
        print("DEBUG: After cleanup for Rock:", data)
        return data

    @staticmethod
    async def create_rock(rock: Rock) -> Rock:
        rock_dict = rock.model_dump()
        encrypted = encrypt_dict(rock_dict.copy(), RockService.EXCLUDE_FIELDS)
        await RockService.rocks.insert_one(encrypted)
        if rock.assigned_to_id:
            await UserService.assign_rock(rock.assigned_to_id, rock.rock_id)
        return rock

    @staticmethod
    async def get_rock(rock_id: UUID) -> Optional[Rock]:
        doc = await RockService.rocks.find_one({"rock_id": str(rock_id)})
        if not doc:
            return None
        data = RockService.safe_decrypt_dict(doc)
        return Rock(**data)

    @staticmethod
    async def get_rock_by_quarter(quarter_id: UUID, rock_id: UUID) -> Optional[Rock]:
        doc = await RockService.rocks.find_one({"quarter_id": str(quarter_id), "rock_id": str(rock_id)})
        if not doc:
            return None
        data = RockService.safe_decrypt_dict(doc)
        return Rock(**data)

    @staticmethod
    async def get_rocks_by_quarter(quarter_id: UUID) -> List[Rock]:
        rocks = []
        async for doc in RockService.rocks.find({"quarter_id": str(quarter_id)}):
            data = RockService.safe_decrypt_dict(doc)
            rocks.append(Rock(**data))
        return rocks

    @staticmethod
    async def get_rocks_with_tasks(quarter_id: UUID, include_comments: bool = False) -> List[Dict]:
        rocks_with_tasks = []
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
        for rock in rocks:
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
        rocks = []
        async for doc in RockService.rocks.find({"assigned_to_id": str(user_id)}):
            data = RockService.safe_decrypt_dict(doc)
            rocks.append(Rock(**data))
        return rocks

    @staticmethod
    async def update_rock(rock_id: UUID, rock_update: Rock) -> Optional[Rock]:
        update_data = rock_update.model_dump(exclude={"id", "rock_id", "created_at"})
        update_data["updated_at"] = datetime.utcnow()
        encrypted = encrypt_dict(update_data.copy(), RockService.EXCLUDE_FIELDS)
        await RockService.rocks.update_one(
            {"rock_id": str(rock_id)},
            {"$set": encrypted}
        )
        if rock_update.assigned_to_id:
            await UserService.assign_rock(rock_update.assigned_to_id, rock_id)
        return await RockService.get_rock(rock_id)

    @staticmethod
    async def update_smart_objective(rock_id: UUID, smart_objective: str) -> Optional[Rock]:
        result = await RockService.rocks.find_one_and_update(
            {"rock_id": str(rock_id)},
            {
                "$set": {
                    "smart_objective": smart_objective,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        return Rock(**RockService.safe_decrypt_dict(result)) if result else None

    @staticmethod
    async def delete_rock(rock_id: UUID) -> bool:
        rock = await RockService.get_rock(rock_id)
        if rock and rock.assigned_to_id:
            await UserService.unassign_rock(rock.assigned_to_id, rock_id)
        result = await RockService.rocks.delete_one({"rock_id": str(rock_id)})
        return result.deleted_count > 0

    @staticmethod
    async def assign_rock(rock_id: UUID, user_id: UUID, user_name: str) -> Optional[Rock]:
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
            await UserService.assign_rock(user_id, rock_id)
            return Rock(**RockService.safe_decrypt_dict(result))
        return None

    @staticmethod
    async def unassign_rock(rock_id: UUID) -> Optional[Rock]:
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
        return Rock(**RockService.safe_decrypt_dict(result)) if result else None

    @staticmethod
    async def get_assignment_info(rock_id: UUID) -> Optional[Dict[str, str]]:
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
        current_rock = await RockService.get_rock_by_quarter(quarter_id, rock_update.rock_id)
        if not current_rock:
            return None, []
        updated_rock = await RockService.update_rock(rock_update.rock_id, rock_update)
        if not updated_rock:
            return None, []
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