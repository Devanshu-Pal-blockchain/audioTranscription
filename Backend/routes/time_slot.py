from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.time_slot import TimeSlot, TimeSlotCreateRequest, TimeSlotUpdateRequest
from models.user import User
from service.time_slot_service import TimeSlotService
from service.auth_service import get_current_user, admin_required

router = APIRouter()

@router.post("/time-slots", response_model=TimeSlot)
async def create_time_slot(
    time_slot_request: TimeSlotCreateRequest,
    current_user: User = Depends(get_current_user)
) -> TimeSlot:
    """Create a new time slot"""
    time_slot = TimeSlot.from_create_request(time_slot_request, current_user.employee_id)
    return await TimeSlotService.create_time_slot(time_slot)

@router.get("/time-slots/{time_slot_id}", response_model=TimeSlot)
async def get_time_slot(
    time_slot_id: UUID,
    current_user: User = Depends(get_current_user)
) -> TimeSlot:
    """Get a time slot by ID"""
    time_slot = await TimeSlotService.get_time_slot(time_slot_id)
    if not time_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time slot not found"
        )
    
    # Check access through meeting
    # Note: This assumes we can check meeting access; in practice, you'd verify through MeetingService
    return time_slot

@router.get("/time-slots", response_model=List[TimeSlot])
async def list_time_slots(
    meeting_id: Optional[UUID] = Query(None, description="Filter by meeting"),
    speaker_id: Optional[UUID] = Query(None, description="Filter by speaker"),
    topic_category: Optional[str] = Query(None, description="Filter by topic category"),
    start_after: Optional[datetime] = Query(None, description="Filter slots starting after this time"),
    end_before: Optional[datetime] = Query(None, description="Filter slots ending before this time"),
    skip: int = Query(0, ge=0, description="Number of time slots to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of time slots to return"),
    current_user: User = Depends(get_current_user)
) -> List[TimeSlot]:
    """List time slots with optional filters"""
    
    return await TimeSlotService.list_time_slots(
        meeting_id=meeting_id,
        speaker_id=speaker_id,
        topic_category=topic_category,
        start_after=start_after,
        end_before=end_before,
        skip=skip,
        limit=limit
    )

@router.put("/time-slots/{time_slot_id}", response_model=TimeSlot)
async def update_time_slot(
    time_slot_id: UUID,
    time_slot_update: TimeSlotUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> TimeSlot:
    """Update a time slot"""
    time_slot = await TimeSlotService.get_time_slot(time_slot_id)
    if not time_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time slot not found"
        )
    
    # Check permissions - admin or creator can update
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != time_slot.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this time slot"
        )
    
    return await TimeSlotService.update_time_slot(time_slot_id, time_slot_update)

@router.delete("/time-slots/{time_slot_id}")
async def delete_time_slot(
    time_slot_id: UUID,
    current_user: User = Depends(admin_required)
) -> Dict[str, str]:
    """Delete a time slot (admin only)"""
    success = await TimeSlotService.delete_time_slot(time_slot_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time slot not found"
        )
    return {"message": "Time slot deleted successfully"}

@router.get("/meetings/{meeting_id}/time-slots", response_model=List[TimeSlot])
async def get_meeting_time_slots(
    meeting_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[TimeSlot]:
    """Get all time slots for a specific meeting"""
    return await TimeSlotService.get_time_slots_by_meeting(meeting_id)

@router.get("/time-slots/{time_slot_id}/transcript", response_model=Dict)
async def get_time_slot_transcript(
    time_slot_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get transcript segment for a specific time slot"""
    time_slot = await TimeSlotService.get_time_slot(time_slot_id)
    if not time_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Time slot not found"
        )
    
    transcript = await TimeSlotService.get_time_slot_transcript(time_slot_id)
    return {
        "time_slot_id": time_slot_id,
        "start_time": time_slot.start_time,
        "end_time": time_slot.end_time,
        "transcript": transcript,
        "speaker": time_slot.speaker_name,
        "topics": time_slot.topics
    }

@router.get("/analytics/speaking-time", response_model=Dict)
async def get_speaking_time_analytics(
    meeting_id: Optional[UUID] = Query(None, description="Filter by meeting"),
    speaker_id: Optional[UUID] = Query(None, description="Filter by speaker"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get speaking time analytics"""
    return await TimeSlotService.get_speaking_time_analytics(
        meeting_id=meeting_id,
        speaker_id=speaker_id,
        date_from=date_from,
        date_to=date_to
    )

@router.get("/analytics/topic-distribution", response_model=Dict)
async def get_topic_distribution(
    meeting_id: Optional[UUID] = Query(None, description="Filter by meeting"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get topic distribution analytics"""
    return await TimeSlotService.get_topic_distribution(
        meeting_id=meeting_id,
        date_from=date_from,
        date_to=date_to
    )

@router.post("/time-slots/bulk-create")
async def bulk_create_time_slots(
    meeting_id: UUID,
    time_slots_data: List[TimeSlotCreateRequest],
    current_user: User = Depends(admin_required)
) -> Dict[str, str]:
    """Bulk create time slots for a meeting (admin only)"""
    success_count = await TimeSlotService.bulk_create_time_slots(
        meeting_id, time_slots_data, current_user.employee_id
    )
    return {
        "message": f"Successfully created {success_count} time slots",
        "meeting_id": str(meeting_id)
    }

@router.get("/speakers/{speaker_id}/time-slots", response_model=List[TimeSlot])
async def get_speaker_time_slots(
    speaker_id: UUID,
    meeting_id: Optional[UUID] = Query(None, description="Filter by meeting"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    skip: int = Query(0, ge=0, description="Number of time slots to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of time slots to return"),
    current_user: User = Depends(get_current_user)
) -> List[TimeSlot]:
    """Get time slots for a specific speaker"""
    return await TimeSlotService.get_speaker_time_slots(
        speaker_id=speaker_id,
        meeting_id=meeting_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit
    )

@router.get("/time-slots/search", response_model=List[TimeSlot])
async def search_time_slots(
    query: str = Query(..., description="Search query for transcript content"),
    meeting_id: Optional[UUID] = Query(None, description="Filter by meeting"),
    speaker_id: Optional[UUID] = Query(None, description="Filter by speaker"),
    skip: int = Query(0, ge=0, description="Number of time slots to skip"),
    limit: int = Query(50, ge=1, le=200, description="Number of time slots to return"),
    current_user: User = Depends(get_current_user)
) -> List[TimeSlot]:
    """Search time slots by transcript content"""
    return await TimeSlotService.search_time_slots(
        query=query,
        meeting_id=meeting_id,
        speaker_id=speaker_id,
        skip=skip,
        limit=limit
    )
