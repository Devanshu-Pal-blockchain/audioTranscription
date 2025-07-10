from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.meeting import Meeting, MeetingCreateRequest, MeetingUpdateRequest
from models.user import User
from service.meeting_service import MeetingService
from service.auth_service import get_current_user, admin_required

router = APIRouter()

@router.post("/meetings", response_model=Meeting)
async def create_meeting(
    meeting_request: MeetingCreateRequest,
    current_user: User = Depends(admin_required)
) -> Meeting:
    """Create a new meeting (admin only)"""
    meeting = Meeting.from_create_request(meeting_request, current_user.employee_id)
    return await MeetingService.create_meeting(meeting)

@router.get("/meetings/{meeting_id}", response_model=Meeting)
async def get_meeting(
    meeting_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Meeting:
    """Get a meeting by ID"""
    meeting = await MeetingService.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    # Check access - users can view meetings they attended or if they're admin
    if (current_user.employee_role != "admin" and 
        current_user.employee_id not in meeting.attendees and
        current_user.employee_id != meeting.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting"
        )
    
    return meeting

@router.get("/meetings", response_model=List[Meeting])
async def list_meetings(
    meeting_type: Optional[str] = Query(None, description="Filter by meeting type"),
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    start_date: Optional[datetime] = Query(None, description="Filter meetings after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter meetings before this date"),
    attendee_id: Optional[UUID] = Query(None, description="Filter by attendee"),
    skip: int = Query(0, ge=0, description="Number of meetings to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of meetings to return"),
    current_user: User = Depends(get_current_user)
) -> List[Meeting]:
    """List meetings with optional filters"""
    
    # Non-admin users can only see their own meetings
    if current_user.employee_role != "admin":
        attendee_id = current_user.employee_id
    
    return await MeetingService.list_meetings(
        meeting_type=meeting_type,
        quarter_id=quarter_id,
        start_date=start_date,
        end_date=end_date,
        attendee_id=attendee_id,
        skip=skip,
        limit=limit
    )

@router.put("/meetings/{meeting_id}", response_model=Meeting)
async def update_meeting(
    meeting_id: UUID,
    meeting_update: MeetingUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> Meeting:
    """Update a meeting"""
    meeting = await MeetingService.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    # Check permissions - only admin or meeting creator can update
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != meeting.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this meeting"
        )
    
    return await MeetingService.update_meeting(meeting_id, meeting_update)

@router.delete("/meetings/{meeting_id}")
async def delete_meeting(
    meeting_id: UUID,
    current_user: User = Depends(admin_required)
) -> Dict[str, str]:
    """Delete a meeting (admin only)"""
    success = await MeetingService.delete_meeting(meeting_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    return {"message": "Meeting deleted successfully"}

@router.get("/meetings/{meeting_id}/summary", response_model=Dict)
async def get_meeting_summary(
    meeting_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get meeting summary with IDS analysis"""
    meeting = await MeetingService.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    # Check access
    if (current_user.employee_role != "admin" and 
        current_user.employee_id not in meeting.attendees and
        current_user.employee_id != meeting.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting"
        )
    
    return await MeetingService.get_meeting_summary(meeting_id)

@router.get("/meetings/{meeting_id}/analytics", response_model=Dict)
async def get_meeting_analytics(
    meeting_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get meeting analytics and insights"""
    meeting = await MeetingService.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    # Check access
    if (current_user.employee_role != "admin" and 
        current_user.employee_id not in meeting.attendees and
        current_user.employee_id != meeting.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting"
        )
    
    return await MeetingService.get_meeting_analytics(meeting_id)

@router.post("/meetings/{meeting_id}/process-transcript")
async def process_transcript(
    meeting_id: UUID,
    current_user: User = Depends(admin_required)
) -> Dict[str, str]:
    """Process meeting transcript for IDS extraction (admin only)"""
    success = await MeetingService.process_transcript(meeting_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found or transcript not available"
        )
    return {"message": "Transcript processed successfully"}

@router.get("/meetings/types/stats", response_model=Dict)
async def get_meeting_type_stats(
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get statistics by meeting type"""
    return await MeetingService.get_meeting_type_stats(
        user_id=current_user.employee_id if current_user.employee_role != "admin" else None
    )
