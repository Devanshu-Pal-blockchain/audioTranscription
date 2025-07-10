from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from models.time_slot import TimeSlot
from .db import get_database

class TimeSlotService:
    @staticmethod
    async def get_collection() -> AsyncIOMotorCollection:
        """Get the time slots collection"""
        db = await get_database()
        return db.time_slots

    @staticmethod
    async def create_time_slot(time_slot_data: Dict[str, Any]) -> TimeSlot:
        """Create a new time slot"""
        collection = await TimeSlotService.get_collection()
        
        # Create time slot instance
        time_slot = TimeSlot(**time_slot_data)
        
        # Insert into database
        result = await collection.insert_one(time_slot.model_dump())
        
        if result.inserted_id:
            return time_slot
        else:
            raise Exception("Failed to create time slot")

    @staticmethod
    async def get_time_slot(slot_id: UUID) -> Optional[TimeSlot]:
        """Get a time slot by ID"""
        collection = await TimeSlotService.get_collection()
        
        time_slot_data = await collection.find_one({"slot_id": slot_id})
        if time_slot_data:
            time_slot_data.pop("_id", None)
            return TimeSlot(**time_slot_data)
        return None

    @staticmethod
    async def get_time_slots_by_meeting(meeting_id: UUID) -> List[TimeSlot]:
        """Get all time slots for a specific meeting, ordered by start time"""
        collection = await TimeSlotService.get_collection()
        
        cursor = collection.find({"meeting_id": meeting_id}).sort("start_time", 1)
        time_slots = []
        
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def get_time_slots_by_category(category: str) -> List[TimeSlot]:
        """Get all time slots by category"""
        collection = await TimeSlotService.get_collection()
        
        cursor = collection.find({"category": category})
        time_slots = []
        
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def get_time_slots_by_participant(participant_name: str) -> List[TimeSlot]:
        """Get all time slots where a specific participant was active"""
        collection = await TimeSlotService.get_collection()
        
        cursor = collection.find({"participants": participant_name})
        time_slots = []
        
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def get_time_slots_by_topic(topic_keyword: str) -> List[TimeSlot]:
        """Get time slots containing a specific topic keyword"""
        collection = await TimeSlotService.get_collection()
        
        cursor = collection.find({"topic": {"$regex": topic_keyword, "$options": "i"}})
        time_slots = []
        
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def get_time_slots_by_urgency(urgency_level: str) -> List[TimeSlot]:
        """Get time slots by urgency level"""
        collection = await TimeSlotService.get_collection()
        
        cursor = collection.find({"urgency_level": urgency_level})
        time_slots = []
        
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def get_high_priority_time_slots() -> List[TimeSlot]:
        """Get time slots with high priority content"""
        collection = await TimeSlotService.get_collection()
        
        cursor = collection.find({
            "$or": [
                {"urgency_level": {"$in": ["high", "critical"]}},
                {"priority_rating": {"$gte": 4}},
                {"issues_identified": {"$not": {"$size": 0}}},
                {"$expr": {"$gte": [{"$size": "$action_items_generated"}, 3]}}
            ]
        })
        
        time_slots = []
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def get_time_slots_with_issues(meeting_id: UUID = None) -> List[TimeSlot]:
        """Get time slots that have identified issues"""
        collection = await TimeSlotService.get_collection()
        
        query = {"issues_identified": {"$not": {"$size": 0}}}
        if meeting_id:
            query["meeting_id"] = meeting_id
            
        cursor = collection.find(query)
        time_slots = []
        
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def get_time_slots_with_solutions(meeting_id: UUID = None) -> List[TimeSlot]:
        """Get time slots that have proposed solutions"""
        collection = await TimeSlotService.get_collection()
        
        query = {"solutions_proposed": {"$not": {"$size": 0}}}
        if meeting_id:
            query["meeting_id"] = meeting_id
            
        cursor = collection.find(query)
        time_slots = []
        
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def update_time_slot(slot_id: UUID, update_data: Dict[str, Any]) -> Optional[TimeSlot]:
        """Update a time slot"""
        collection = await TimeSlotService.get_collection()
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"slot_id": slot_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await TimeSlotService.get_time_slot(slot_id)
        return None

    @staticmethod
    async def add_issue_reference(slot_id: UUID, issue_id: UUID) -> Optional[TimeSlot]:
        """Add an issue reference to a time slot"""
        collection = await TimeSlotService.get_collection()
        
        result = await collection.update_one(
            {"slot_id": slot_id},
            {
                "$addToSet": {"issues_identified": issue_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await TimeSlotService.get_time_slot(slot_id)
        return None

    @staticmethod
    async def add_solution_reference(slot_id: UUID, solution_id: UUID) -> Optional[TimeSlot]:
        """Add a solution reference to a time slot"""
        collection = await TimeSlotService.get_collection()
        
        result = await collection.update_one(
            {"slot_id": slot_id},
            {
                "$addToSet": {"solutions_proposed": solution_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await TimeSlotService.get_time_slot(slot_id)
        return None

    @staticmethod
    async def add_key_point(slot_id: UUID, key_point: str) -> Optional[TimeSlot]:
        """Add a key point to a time slot"""
        collection = await TimeSlotService.get_collection()
        
        result = await collection.update_one(
            {"slot_id": slot_id},
            {
                "$addToSet": {"key_points": key_point},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await TimeSlotService.get_time_slot(slot_id)
        return None

    @staticmethod
    async def add_outcome(slot_id: UUID, outcome: str) -> Optional[TimeSlot]:
        """Add an outcome to a time slot"""
        collection = await TimeSlotService.get_collection()
        
        result = await collection.update_one(
            {"slot_id": slot_id},
            {
                "$addToSet": {"outcomes": outcome},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await TimeSlotService.get_time_slot(slot_id)
        return None

    @staticmethod
    async def add_decision_made(slot_id: UUID, decision: str) -> Optional[TimeSlot]:
        """Add a decision to a time slot"""
        collection = await TimeSlotService.get_collection()
        
        result = await collection.update_one(
            {"slot_id": slot_id},
            {
                "$addToSet": {"decisions_made": decision},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await TimeSlotService.get_time_slot(slot_id)
        return None

    @staticmethod
    async def add_action_item(slot_id: UUID, action_item: str) -> Optional[TimeSlot]:
        """Add an action item to a time slot"""
        collection = await TimeSlotService.get_collection()
        
        result = await collection.update_one(
            {"slot_id": slot_id},
            {
                "$addToSet": {"action_items_generated": action_item},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await TimeSlotService.get_time_slot(slot_id)
        return None

    @staticmethod
    async def link_time_slots(previous_slot_id: UUID, next_slot_id: UUID) -> bool:
        """Link two consecutive time slots"""
        collection = await TimeSlotService.get_collection()
        
        # Update previous slot to point to next
        result1 = await collection.update_one(
            {"slot_id": previous_slot_id},
            {"$set": {"next_slot": next_slot_id, "updated_at": datetime.utcnow()}}
        )
        
        # Update next slot to point to previous
        result2 = await collection.update_one(
            {"slot_id": next_slot_id},
            {"$set": {"previous_slot": previous_slot_id, "updated_at": datetime.utcnow()}}
        )
        
        return result1.modified_count > 0 and result2.modified_count > 0

    @staticmethod
    async def delete_time_slot(slot_id: UUID) -> bool:
        """Delete a time slot"""
        collection = await TimeSlotService.get_collection()
        
        result = await collection.delete_one({"slot_id": slot_id})
        return result.deleted_count > 0

    @staticmethod
    async def get_all_time_slots() -> List[TimeSlot]:
        """Get all time slots"""
        collection = await TimeSlotService.get_collection()
        
        cursor = collection.find({})
        time_slots = []
        
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def search_time_slots(search_term: str) -> List[TimeSlot]:
        """Search time slots by topic, key points, or outcomes"""
        collection = await TimeSlotService.get_collection()
        
        # Case-insensitive search in topic, key_points, and outcomes
        cursor = collection.find({
            "$or": [
                {"topic": {"$regex": search_term, "$options": "i"}},
                {"key_points": {"$regex": search_term, "$options": "i"}},
                {"outcomes": {"$regex": search_term, "$options": "i"}},
                {"transcript_segment": {"$regex": search_term, "$options": "i"}}
            ]
        })
        
        time_slots = []
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
            
        return time_slots

    @staticmethod
    async def get_meeting_timeline(meeting_id: UUID) -> List[TimeSlot]:
        """Get complete timeline of time slots for a meeting"""
        return await TimeSlotService.get_time_slots_by_meeting(meeting_id)

    @staticmethod
    async def get_time_slot_statistics(meeting_id: UUID = None) -> Dict[str, Any]:
        """Get time slot statistics"""
        collection = await TimeSlotService.get_collection()
        
        # Base query filter
        base_query = {}
        if meeting_id:
            base_query["meeting_id"] = meeting_id
        
        # Count by category
        categories = ["issues", "solutions", "decisions", "planning", "discussion", "review", "other"]
        category_counts = {}
        for category in categories:
            query = {**base_query, "category": category}
            category_counts[category] = await collection.count_documents(query)
        
        # Count by urgency level
        urgency_levels = ["critical", "high", "medium", "low"]
        urgency_counts = {}
        for urgency in urgency_levels:
            query = {**base_query, "urgency_level": urgency}
            urgency_counts[urgency] = await collection.count_documents(query)
        
        # Count slots with issues/solutions
        slots_with_issues = await collection.count_documents({
            **base_query,
            "issues_identified": {"$not": {"$size": 0}}
        })
        
        slots_with_solutions = await collection.count_documents({
            **base_query,
            "solutions_proposed": {"$not": {"$size": 0}}
        })
        
        # Average engagement score
        pipeline = [
            {"$match": base_query},
            {"$addFields": {
                "engagement_score": {
                    "$add": [
                        {"$multiply": [{"$size": "$participants"}, 10]},
                        {"$multiply": [{"$size": "$key_points"}, 5]},
                        {"$multiply": [{"$size": "$outcomes"}, 10]},
                        {"$multiply": [{"$size": "$action_items_generated"}, 15]}
                    ]
                }
            }},
            {"$group": {"_id": None, "avg_engagement": {"$avg": "$engagement_score"}}}
        ]
        
        avg_result = await collection.aggregate(pipeline).to_list(1)
        avg_engagement = avg_result[0]["avg_engagement"] if avg_result else 0
        
        # Total duration
        pipeline = [
            {"$match": base_query},
            {"$group": {"_id": None, "total_duration": {"$sum": "$duration_seconds"}}}
        ]
        
        duration_result = await collection.aggregate(pipeline).to_list(1)
        total_duration = duration_result[0]["total_duration"] if duration_result else 0
        
        # Total count
        total_count = await collection.count_documents(base_query)
        
        return {
            "by_category": category_counts,
            "by_urgency": urgency_counts,
            "content_analysis": {
                "slots_with_issues": slots_with_issues,
                "slots_with_solutions": slots_with_solutions,
                "issue_solution_ratio": round(slots_with_solutions / slots_with_issues, 2) if slots_with_issues > 0 else 0
            },
            "engagement": {
                "average_engagement_score": round(avg_engagement, 2),
                "total_duration_minutes": round(total_duration / 60, 2)
            },
            "total": total_count
        }

    @staticmethod
    async def bulk_create_time_slots(time_slots_data: List[Dict[str, Any]]) -> List[TimeSlot]:
        """Bulk create multiple time slots"""
        collection = await TimeSlotService.get_collection()
        
        # Create time slot instances
        time_slots = [TimeSlot(**time_slot_data) for time_slot_data in time_slots_data]
        
        # Bulk insert
        time_slot_dicts = [time_slot.model_dump() for time_slot in time_slots]
        result = await collection.insert_many(time_slot_dicts)
        
        if result.inserted_ids:
            return time_slots
        else:
            raise Exception("Failed to create time slots")

    @staticmethod
    async def get_participant_activity(participant_name: str, meeting_id: UUID = None) -> Dict[str, Any]:
        """Get activity analysis for a specific participant"""
        collection = await TimeSlotService.get_collection()
        
        base_query = {"participants": participant_name}
        if meeting_id:
            base_query["meeting_id"] = meeting_id
        
        # Get all time slots where participant was active
        cursor = collection.find(base_query)
        time_slots = []
        
        async for time_slot_data in cursor:
            time_slot_data.pop("_id", None)
            time_slots.append(TimeSlot(**time_slot_data))
        
        if not time_slots:
            return {"participant": participant_name, "activity": "No activity found"}
        
        # Calculate statistics
        total_slots = len(time_slots)
        total_duration = sum(slot.duration_seconds for slot in time_slots)
        categories = {}
        urgency_levels = {}
        
        for slot in time_slots:
            categories[slot.category] = categories.get(slot.category, 0) + 1
            urgency_levels[slot.urgency_level] = urgency_levels.get(slot.urgency_level, 0) + 1
        
        return {
            "participant": participant_name,
            "total_active_slots": total_slots,
            "total_active_duration_minutes": round(total_duration / 60, 2),
            "activity_by_category": categories,
            "activity_by_urgency": urgency_levels,
            "most_active_category": max(categories.items(), key=lambda x: x[1])[0] if categories else None,
            "average_slot_duration_minutes": round((total_duration / total_slots) / 60, 2) if total_slots > 0 else 0
        }
