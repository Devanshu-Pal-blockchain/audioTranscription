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
        import uuid
        from datetime import datetime
        if not doc:
            return {}
        if "data_enc" in doc:
            data = decrypt_dict(doc, RockService.EXCLUDE_FIELDS, RockService.EXCLUDE_TYPES)
        else:
            data = doc.copy()

        # Ensure all required fields are present and correctly typed
        # UUID fields
        for field in ["id", "rock_id", "quarter_id"]:
            val = data.get(field)
            if not val:
                data[field] = uuid.uuid4()
            elif isinstance(val, str):
                try:
                    data[field] = uuid.UUID(val)
                except Exception:
                    data[field] = uuid.uuid4()

        # Optional UUID
        if "assigned_to_id" in data:
            val = data["assigned_to_id"]
            if val in (None, ""):
                data["assigned_to_id"] = None
            elif isinstance(val, str):
                try:
                    data["assigned_to_id"] = uuid.UUID(val)
                except Exception:
                    data["assigned_to_id"] = None

        # Datetime fields
        for field in ["created_at", "updated_at"]:
            val = data.get(field)
            if not val:
                data[field] = datetime.utcnow()
            elif isinstance(val, str):
                try:
                    data[field] = datetime.fromisoformat(val)
                except Exception:
                    data[field] = datetime.utcnow()

        # Strings
        if not data.get("rock_name"):
            data["rock_name"] = "Untitled Rock"
        if not data.get("smart_objective"):
            data["smart_objective"] = data["rock_name"]
        if data.get("assigned_to_name") is None:
            data["assigned_to_name"] = ""

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
    
    @staticmethod
    async def update_rock_field(rock_id: UUID, field: str, value) -> Optional[Rock]:
        """Update a specific field of a rock"""
        if field not in ["status", "assigned_to_id", "assigned_to_name", "rock_name", "smart_objective"]:
            return None
            
        update_data = {field: value, "updated_at": datetime.utcnow()}
        
        # Encrypt the update data
        encrypted = encrypt_dict(update_data.copy(), RockService.EXCLUDE_FIELDS)
        
        result = await RockService.collection.find_one_and_update(
            {"id": rock_id},
            {"$set": encrypted},
            return_document=True
        )
        
        if result:
            decrypted_data = RockService.safe_decrypt_dict(result)
            return Rock(**decrypted_data)
        return None 