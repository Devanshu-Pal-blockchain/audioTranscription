from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorCollection
from models.meeting import Meeting, MeetingTimeline
from .db import get_database

class MeetingService:
    @staticmethod
    async def get_collection() -> AsyncIOMotorCollection:
        """Get the meetings collection"""
        db = await get_database()
        return db.meetings

    @staticmethod
    async def create_meeting(meeting_data: Dict[str, Any]) -> Meeting:
        """Create a new meeting"""
        collection = await MeetingService.get_collection()
        
        # Create meeting instance
        meeting = Meeting(**meeting_data)
        
        # Insert into database
        result = await collection.insert_one(meeting.model_dump())
        
        if result.inserted_id:
            return meeting
        else:
            raise Exception("Failed to create meeting")

    @staticmethod
    async def get_meeting(meeting_id: UUID) -> Optional[Meeting]:
        """Get a meeting by ID"""
        collection = await MeetingService.get_collection()
        
        meeting_data = await collection.find_one({"meeting_id": meeting_id})
        if meeting_data:
            meeting_data.pop("_id", None)
            return Meeting(**meeting_data)
        return None

    @staticmethod
    async def get_meetings_by_type(meeting_type: str) -> List[Meeting]:
        """Get all meetings of a specific type"""
        collection = await MeetingService.get_collection()
        
        cursor = collection.find({"meeting_type": meeting_type})
        meetings = []
        
        async for meeting_data in cursor:
            meeting_data.pop("_id", None)
            meetings.append(Meeting(**meeting_data))
            
        return meetings

    @staticmethod
    async def get_meetings_by_timeline(year: int, quarter: Optional[int] = None, week: Optional[int] = None) -> List[Meeting]:
        """Get meetings by timeline parameters"""
        collection = await MeetingService.get_collection()
        
        # Build query based on timeline parameters
        query = {"timeline.year": year}
        if quarter:
            query["timeline.quarter"] = quarter
        if week:
            query["timeline.week"] = week
            
        cursor = collection.find(query)
        meetings = []
        
        async for meeting_data in cursor:
            meeting_data.pop("_id", None)
            meetings.append(Meeting(**meeting_data))
            
        return meetings

    @staticmethod
    async def get_meetings_by_participant(participant_id: UUID) -> List[Meeting]:
        """Get all meetings where a user participated"""
        collection = await MeetingService.get_collection()
        
        cursor = collection.find({"participants": participant_id})
        meetings = []
        
        async for meeting_data in cursor:
            meeting_data.pop("_id", None)
            meetings.append(Meeting(**meeting_data))
            
        return meetings

    @staticmethod
    async def update_meeting(meeting_id: UUID, update_data: Dict[str, Any]) -> Optional[Meeting]:
        """Update a meeting"""
        collection = await MeetingService.get_collection()
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        result = await collection.update_one(
            {"meeting_id": meeting_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return await MeetingService.get_meeting(meeting_id)
        return None

    @staticmethod
    async def update_meeting_status(meeting_id: UUID, status: str) -> Optional[Meeting]:
        """Update meeting status"""
        return await MeetingService.update_meeting(meeting_id, {"status": status})

    @staticmethod
    async def add_participant(meeting_id: UUID, participant_id: UUID) -> Optional[Meeting]:
        """Add a participant to a meeting"""
        collection = await MeetingService.get_collection()
        
        result = await collection.update_one(
            {"meeting_id": meeting_id},
            {
                "$addToSet": {"participants": participant_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await MeetingService.get_meeting(meeting_id)
        return None

    @staticmethod
    async def remove_participant(meeting_id: UUID, participant_id: UUID) -> Optional[Meeting]:
        """Remove a participant from a meeting"""
        collection = await MeetingService.get_collection()
        
        result = await collection.update_one(
            {"meeting_id": meeting_id},
            {
                "$pull": {"participants": participant_id},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            return await MeetingService.get_meeting(meeting_id)
        return None

    @staticmethod
    async def set_audio_file_path(meeting_id: UUID, file_path: str) -> Optional[Meeting]:
        """Set the audio file path for a meeting"""
        return await MeetingService.update_meeting(meeting_id, {"audio_file_path": file_path})

    @staticmethod
    async def set_transcript_file_path(meeting_id: UUID, file_path: str) -> Optional[Meeting]:
        """Set the transcript file path for a meeting"""
        return await MeetingService.update_meeting(meeting_id, {"transcript_file_path": file_path})

    @staticmethod
    async def delete_meeting(meeting_id: UUID) -> bool:
        """Delete a meeting"""
        collection = await MeetingService.get_collection()
        
        result = await collection.delete_one({"meeting_id": meeting_id})
        return result.deleted_count > 0

    @staticmethod
    async def get_all_meetings() -> List[Meeting]:
        """Get all meetings"""
        collection = await MeetingService.get_collection()
        
        cursor = collection.find({})
        meetings = []
        
        async for meeting_data in cursor:
            meeting_data.pop("_id", None)
            meetings.append(Meeting(**meeting_data))
            
        return meetings

    @staticmethod
    async def get_meetings_by_status(status: str) -> List[Meeting]:
        """Get meetings by status"""
        collection = await MeetingService.get_collection()
        
        cursor = collection.find({"status": status})
        meetings = []
        
        async for meeting_data in cursor:
            meeting_data.pop("_id", None)
            meetings.append(Meeting(**meeting_data))
            
        return meetings

    @staticmethod
    async def get_recent_meetings(limit: int = 10) -> List[Meeting]:
        """Get recent meetings ordered by creation date"""
        collection = await MeetingService.get_collection()
        
        cursor = collection.find({}).sort("created_at", -1).limit(limit)
        meetings = []
        
        async for meeting_data in cursor:
            meeting_data.pop("_id", None)
            meetings.append(Meeting(**meeting_data))
            
        return meetings

    @staticmethod
    async def validate_meeting_timeline(meeting_type: str, timeline: MeetingTimeline) -> List[str]:
        """Validate meeting timeline parameters"""
        issues = []
        
        if meeting_type == "yearly":
            if timeline.quarter is not None or timeline.week is not None:
                issues.append("Yearly meetings should not have quarter or week specified")
        elif meeting_type == "quarterly":
            if timeline.quarter is None:
                issues.append("Quarterly meetings must have quarter specified")
            if timeline.week is not None:
                issues.append("Quarterly meetings should not have week specified")
        elif meeting_type == "weekly":
            if timeline.quarter is None or timeline.week is None:
                issues.append("Weekly meetings must have both quarter and week specified")
                
        return issues

    @staticmethod
    async def get_meeting_statistics() -> Dict[str, Any]:
        """Get meeting statistics"""
        collection = await MeetingService.get_collection()
        
        # Count by type
        yearly_count = await collection.count_documents({"meeting_type": "yearly"})
        quarterly_count = await collection.count_documents({"meeting_type": "quarterly"})
        weekly_count = await collection.count_documents({"meeting_type": "weekly"})
        
        # Count by status
        draft_count = await collection.count_documents({"status": "draft"})
        in_progress_count = await collection.count_documents({"status": "in_progress"})
        completed_count = await collection.count_documents({"status": "completed"})
        
        return {
            "by_type": {
                "yearly": yearly_count,
                "quarterly": quarterly_count,
                "weekly": weekly_count,
                "total": yearly_count + quarterly_count + weekly_count
            },
            "by_status": {
                "draft": draft_count,
                "in_progress": in_progress_count,
                "completed": completed_count,
                "total": draft_count + in_progress_count + completed_count
            }
        }
