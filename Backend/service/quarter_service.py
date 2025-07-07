from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException
from models.quarter import Quarter
from .db import db
from .rock_service import RockService
from datetime import datetime

class QuarterService:
    collection = db.quarters

    @staticmethod
    async def create_quarter(quarter: Quarter) -> Quarter:
        """Create a new quarter"""
        quarter_dict = quarter.model_dump()
        # Remove status field if it's None to avoid storing null values
        if quarter_dict.get('status') is None:
            quarter_dict.pop('status', None)
        result = await QuarterService.collection.insert_one(quarter_dict)
        return quarter

    @staticmethod
    async def get_quarter(quarter_id: UUID) -> Optional[Quarter]:
        """Get a quarter by ID"""
        # Try both UUID object and string formats to handle different storage formats
        quarter_dict = await QuarterService.collection.find_one({"id": quarter_id})
        if not quarter_dict:
            quarter_dict = await QuarterService.collection.find_one({"id": str(quarter_id)})
        return Quarter(**quarter_dict) if quarter_dict else None

    @staticmethod
    async def get_quarters(year: Optional[int] = None, status: Optional[int] = None) -> List[Quarter]:
        """Get all quarters, optionally filtered by year and status"""
        filter_dict = {}
        if year is not None:
            filter_dict["year"] = year
        if status is not None:
            filter_dict["status"] = status
        
        quarters = []
        async for quarter in QuarterService.collection.find(filter_dict):
            quarters.append(Quarter(**quarter))
        return quarters

    @staticmethod
    async def update_quarter(quarter_id: UUID, quarter_update: Quarter) -> Optional[Quarter]:
        """Update a quarter"""
        update_data = quarter_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = quarter_update.updated_at
        
        # Try both UUID object and string formats
        result = await QuarterService.collection.find_one_and_update(
            {"id": quarter_id},
            {"$set": update_data},
            return_document=True
        )
        if not result:
            result = await QuarterService.collection.find_one_and_update(
                {"id": str(quarter_id)},
                {"$set": update_data},
                return_document=True
            )
        return Quarter(**result) if result else None

    @staticmethod
    async def delete_quarter(quarter_id: UUID) -> bool:
        """Delete a quarter and associated rocks"""
        # Get all rocks for this quarter
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
        
        # Delete all associated rocks first
        for rock in rocks:
            await RockService.delete_rock(rock.rock_id)

        # Delete the quarter - try both UUID object and string formats
        result = await QuarterService.collection.delete_one({"id": quarter_id})
        if result.deleted_count == 0:
            result = await QuarterService.collection.delete_one({"id": str(quarter_id)})
        return result.deleted_count > 0

    @staticmethod
    async def add_participant(quarter_id: UUID, user_id: UUID) -> Optional[Quarter]:
        """Add a participant to a quarter"""
        # Try both UUID object and string formats
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
        return Quarter(**result) if result else None

    @staticmethod
    async def remove_participant(quarter_id: UUID, user_id: UUID) -> Optional[Quarter]:
        """Remove a participant from a quarter"""
        # Try both UUID object and string formats
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
        return Quarter(**result) if result else None

    @staticmethod
    async def get_quarters_by_participant(user_id: UUID) -> List[Quarter]:
        """Get all quarters where a user is a participant"""
        quarters = []
        async for quarter in QuarterService.collection.find({"participants": str(user_id)}):
            quarters.append(Quarter(**quarter))
        return quarters

    @staticmethod
    async def update_quarter_field(quarter_id: UUID, field: str, value) -> Optional[Quarter]:
        """Update a specific field of a quarter"""
        if field not in ["weeks", "year", "title", "description", "status"]:
            return None
            
        # Try both UUID object and string formats
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
        return Quarter(**result) if result else None

    @staticmethod
    async def get_quarters_by_status(status: int) -> List[Quarter]:
        """Get all quarters with a specific status"""
        quarters = []
        async for quarter in QuarterService.collection.find({"status": status}):
            quarters.append(Quarter(**quarter))
        return quarters 