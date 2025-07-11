from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from models.quarter import Quarter
from .db import db
from .rock_service import RockService
from datetime import datetime
from utils.secure_fields import encrypt_dict, decrypt_dict, fill_required_fields

class QuarterService:
    collection = db.quarters
    EXCLUDE_FIELDS = ["id", "created_at", "updated_at", "participants"]
    EXCLUDE_TYPES = {
        "id": UUID,
        "participants": List[UUID],
        "created_at": datetime,
        "updated_at": datetime
    }

    @staticmethod
    def safe_decrypt_dict(doc):
        if not doc:
            return {}
        if "data_enc" in doc:
            data = decrypt_dict(doc, QuarterService.EXCLUDE_FIELDS, QuarterService.EXCLUDE_TYPES)
        else:
            data = doc
        data = fill_required_fields(data, "quarter")
        return data

    @staticmethod
    async def create_quarter(quarter: Quarter) -> Quarter:
        quarter_dict = quarter.model_dump()
        encrypted = encrypt_dict(quarter_dict.copy(), QuarterService.EXCLUDE_FIELDS)
        await QuarterService.collection.insert_one(encrypted)
        return quarter

    @staticmethod
    async def get_quarter(quarter_id: UUID) -> Optional[Quarter]:
        doc = await QuarterService.collection.find_one({"id": quarter_id})
        if not doc:
            doc = await QuarterService.collection.find_one({"id": str(quarter_id)})
        if not doc:
            return None
        data = QuarterService.safe_decrypt_dict(doc)
        return Quarter(**data)

    @staticmethod
    async def get_quarters(year: Optional[int] = None, status: Optional[int] = None) -> List[Quarter]:
        filter_dict = {}
        if year is not None:
            filter_dict["year"] = year
        if status is not None:
            filter_dict["status"] = status
        quarters = []
        async for doc in QuarterService.collection.find(filter_dict):
            data = QuarterService.safe_decrypt_dict(doc)
            quarters.append(Quarter(**data))
        return quarters

    @staticmethod
    async def update_quarter(quarter_id: UUID, quarter_update: Quarter) -> Optional[Quarter]:
        update_data = quarter_update.model_dump(exclude_unset=True)
        encrypted = encrypt_dict(update_data.copy(), QuarterService.EXCLUDE_FIELDS)
        result = await QuarterService.collection.find_one_and_update(
            {"id": quarter_id},
            {"$set": encrypted},
            return_document=True
        )
        if not result:
            result = await QuarterService.collection.find_one_and_update(
                {"id": str(quarter_id)},
                {"$set": encrypted},
                return_document=True
            )
        return Quarter(**QuarterService.safe_decrypt_dict(result)) if result else None

    @staticmethod
    async def delete_quarter(quarter_id: UUID) -> bool:
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
        for rock in rocks:
            await RockService.delete_rock(rock.rock_id)
        result = await QuarterService.collection.delete_one({"id": quarter_id})
        if result.deleted_count == 0:
            result = await QuarterService.collection.delete_one({"id": str(quarter_id)})
        return result.deleted_count > 0

    @staticmethod
    async def add_participant(quarter_id: UUID, user_id: UUID) -> Optional[Quarter]:
        result = await QuarterService.collection.find_one_and_update(
            {"id": quarter_id},
            {"$addToSet": {"participants": user_id}},
            return_document=True
        )
        if not result:
            result = await QuarterService.collection.find_one_and_update(
                {"id": str(quarter_id)},
                {"$addToSet": {"participants": user_id}},
                return_document=True
            )
        return Quarter(**QuarterService.safe_decrypt_dict(result)) if result else None

    @staticmethod
    async def remove_participant(quarter_id: UUID, user_id: UUID) -> Optional[Quarter]:
        result = await QuarterService.collection.find_one_and_update(
            {"id": quarter_id},
            {"$pull": {"participants": user_id}},
            return_document=True
        )
        if not result:
            result = await QuarterService.collection.find_one_and_update(
                {"id": str(quarter_id)},
                {"$pull": {"participants": user_id}},
                return_document=True
            )
        return Quarter(**QuarterService.safe_decrypt_dict(result)) if result else None

    @staticmethod
    async def get_quarters_by_participant(user_id: UUID) -> List[Quarter]:
        quarters = []
        async for doc in QuarterService.collection.find({"participants": str(user_id)}):
            data = QuarterService.safe_decrypt_dict(doc)
            quarters.append(Quarter(**data))
        return quarters

    @staticmethod
    async def update_quarter_field(quarter_id: UUID, field: str, value) -> Optional[Quarter]:
        if field not in ["weeks", "year", "title", "description", "status"]:
            return None
        result = await QuarterService.collection.find_one_and_update(
            {"id": quarter_id},
            {
                "$set": {
                    field: value,
                    "updated_at": datetime.utcnow()
                }
            },
            return_document=True
        )
        if not result:
            result = await QuarterService.collection.find_one_and_update(
                {"id": str(quarter_id)},
                {
                    "$set": {
                        field: value,
                        "updated_at": datetime.utcnow()
                    }
                },
                return_document=True
            )
        return Quarter(**QuarterService.safe_decrypt_dict(result)) if result else None

    @staticmethod
    async def get_quarters_by_status(status: int) -> List[Quarter]:
        quarters = []
        async for doc in QuarterService.collection.find({"status": status}):
            data = QuarterService.safe_decrypt_dict(doc)
            quarters.append(Quarter(**data))
        return quarters 