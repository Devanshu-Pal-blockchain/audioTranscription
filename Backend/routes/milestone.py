from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.milestone import Milestone, MilestoneCreateRequest, MilestoneUpdateRequest
from models.user import User
from service.milestone_service import MilestoneService
from service.auth_service import get_current_user, admin_required

router = APIRouter()

@router.post("/milestones", response_model=Milestone)
async def create_milestone(
    milestone_request: MilestoneCreateRequest,
    current_user: User = Depends(get_current_user)
) -> Milestone:
    """Create a new milestone"""
    milestone = Milestone.from_create_request(milestone_request, current_user.employee_id)
    return await MilestoneService.create_milestone(milestone)

@router.get("/milestones/{milestone_id}", response_model=Milestone)
async def get_milestone(
    milestone_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Milestone:
    """Get a milestone by ID"""
    milestone = await MilestoneService.get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    
    # Check access - users can view milestones they created, are assigned to, or if they're admin
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != milestone.created_by and
        current_user.employee_id != milestone.assigned_to and
        current_user.employee_id not in milestone.stakeholders):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this milestone"
        )
    
    return milestone

@router.get("/milestones", response_model=List[Milestone])
async def list_milestones(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    milestone_type: Optional[str] = Query(None, description="Filter by type"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assignee"),
    rock_id: Optional[UUID] = Query(None, description="Filter by rock"),
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    due_before: Optional[datetime] = Query(None, description="Filter by due date"),
    skip: int = Query(0, ge=0, description="Number of milestones to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of milestones to return"),
    current_user: User = Depends(get_current_user)
) -> List[Milestone]:
    """List milestones with optional filters"""
    
    # Non-admin users see milestones they're involved with
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await MilestoneService.list_milestones(
        status=status_filter,
        milestone_type=milestone_type,
        assigned_to=assigned_to,
        rock_id=rock_id,
        quarter_id=quarter_id,
        due_before=due_before,
        user_filter=user_filter,
        skip=skip,
        limit=limit
    )

@router.put("/milestones/{milestone_id}", response_model=Milestone)
async def update_milestone(
    milestone_id: UUID,
    milestone_update: MilestoneUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> Milestone:
    """Update a milestone"""
    milestone = await MilestoneService.get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    
    # Check permissions - admin, creator, or assignee can update
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != milestone.created_by and
        current_user.employee_id != milestone.assigned_to):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this milestone"
        )
    
    return await MilestoneService.update_milestone(milestone_id, milestone_update)

@router.delete("/milestones/{milestone_id}")
async def delete_milestone(
    milestone_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete a milestone"""
    milestone = await MilestoneService.get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    
    # Check permissions - admin or creator can delete
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != milestone.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this milestone"
        )
    
    success = await MilestoneService.delete_milestone(milestone_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete milestone"
        )
    return {"message": "Milestone deleted successfully"}

@router.get("/milestones/{milestone_id}/progress", response_model=Dict)
async def get_milestone_progress(
    milestone_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get detailed progress information for a milestone"""
    milestone = await MilestoneService.get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    
    # Check access
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != milestone.created_by and
        current_user.employee_id != milestone.assigned_to and
        current_user.employee_id not in milestone.stakeholders):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this milestone"
        )
    
    return await MilestoneService.get_milestone_progress(milestone_id)

@router.post("/milestones/{milestone_id}/update-progress")
async def update_milestone_progress(
    milestone_id: UUID,
    progress_percentage: float = Query(..., ge=0.0, le=100.0, description="Progress percentage"),
    progress_notes: Optional[str] = Query(None, description="Progress notes"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Update milestone progress"""
    milestone = await MilestoneService.get_milestone(milestone_id)
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Milestone not found"
        )
    
    # Check permissions - admin, creator, or assignee can update progress
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != milestone.created_by and
        current_user.employee_id != milestone.assigned_to):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this milestone"
        )
    
    success = await MilestoneService.update_milestone_progress(
        milestone_id, progress_percentage, progress_notes, current_user.employee_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update milestone progress"
        )
    return {"message": "Milestone progress updated successfully"}

@router.get("/rocks/{rock_id}/milestones", response_model=List[Milestone])
async def get_rock_milestones(
    rock_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Milestone]:
    """Get all milestones for a specific rock"""
    return await MilestoneService.get_milestones_by_rock(rock_id, current_user.employee_id)

@router.get("/analytics/milestone-stats", response_model=Dict)
async def get_milestone_stats(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    rock_id: Optional[UUID] = Query(None, description="Filter by rock"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get milestone statistics and analytics"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    return await MilestoneService.get_milestone_stats(quarter_id, rock_id, user_filter)

@router.get("/milestones/upcoming", response_model=List[Milestone])
async def get_upcoming_milestones(
    days_ahead: int = Query(30, ge=1, le=365, description="Number of days to look ahead"),
    current_user: User = Depends(get_current_user)
) -> List[Milestone]:
    """Get upcoming milestones within the specified timeframe"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    return await MilestoneService.get_upcoming_milestones(days_ahead, user_filter)

@router.get("/milestones/overdue", response_model=List[Milestone])
async def get_overdue_milestones(
    current_user: User = Depends(get_current_user)
) -> List[Milestone]:
    """Get overdue milestones"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    return await MilestoneService.get_overdue_milestones(user_filter)
