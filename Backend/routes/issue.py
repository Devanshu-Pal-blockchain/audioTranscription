from typing import List, Optional, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.issue import Issue
from service.issue_service import IssueService
from service.quarter_service import QuarterService
from service.auth_service import get_current_user, facilitator_required
from models.user import User
from datetime import datetime

router = APIRouter()

@router.post("/issues", response_model=Issue)
async def create_issue(
    issue: Issue,
    current_user: User = Depends(get_current_user)
) -> Issue:
    """Create a new issue"""
    # Verify quarter exists
    quarter = await QuarterService.get_quarter(issue.quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    
    created_issue = await IssueService.create_issue(issue)
    if not created_issue:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create issue"
        )
    return created_issue

@router.get("/issues/{issue_id}", response_model=Issue)
async def get_issue(
    issue_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Issue:
    """Get an issue by ID"""
    issue = await IssueService.get_issue(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    return issue

@router.get("/quarters/{quarter_id}/issues", response_model=List[Issue])
async def get_issues_by_quarter(
    quarter_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Issue]:
    """Get all issues for a specific quarter"""
    # Verify quarter exists
    quarter = await QuarterService.get_quarter(quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    
    return await IssueService.get_issues_by_quarter(quarter_id)

@router.get("/users/{user_id}/issues", response_model=List[Issue])
async def get_issues_by_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Issue]:
    """Get all issues raised by a specific user"""
    # Check if user can access these issues
    if (current_user.employee_role != "facilitator" and 
        str(user_id) != str(current_user.employee_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own issues"
        )
    
    return await IssueService.get_issues_by_user(user_id)

@router.get("/issues", response_model=List[Issue])
async def get_issues_by_status(
    status: str,
    quarter_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user)
) -> List[Issue]:
    """Get issues by status, optionally filtered by quarter"""
    return await IssueService.get_issues_by_status(status, quarter_id)

@router.get("/issues/solution-type/{solution_type}", response_model=List[Issue])
async def get_issues_by_solution_type(
    solution_type: str,
    quarter_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user)
) -> List[Issue]:
    """Get issues by linked solution type (rock, todo, runtime_solution)"""
    if solution_type not in ["rock", "todo", "runtime_solution"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid solution type. Must be 'rock', 'todo', or 'runtime_solution'"
        )
    
    return await IssueService.get_issues_by_solution_type(solution_type, quarter_id)

@router.get("/issues/search", response_model=List[Issue])
async def search_issues(
    q: str = Query(..., min_length=1),
    quarter_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user)
) -> List[Issue]:
    """Search issues by title or description"""
    return await IssueService.search_issues(q, quarter_id)

@router.put("/issues/{issue_id}", response_model=Issue)
async def update_issue(
    issue_id: UUID,
    update_data: Dict,
    current_user: User = Depends(get_current_user)
) -> Issue:
    """Update an issue"""
    # Get existing issue
    existing_issue = await IssueService.get_issue(issue_id)
    if not existing_issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Check permissions - only facilitator or issue raiser can update
    if (current_user.employee_role != "facilitator" and 
        existing_issue.raised_by_id and 
        str(existing_issue.raised_by_id) != str(current_user.employee_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update issues you raised"
        )
    
    updated_issue = await IssueService.update_issue(issue_id, update_data)
    if not updated_issue:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update issue"
        )
    
    return updated_issue

@router.delete("/issues/{issue_id}")
async def delete_issue(
    issue_id: UUID,
    current_user: User = Depends(facilitator_required)
) -> Dict[str, str]:
    """Delete an issue (facilitator only)"""
    success = await IssueService.delete_issue(issue_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    return {"message": "Issue deleted successfully"}

@router.get("/issues/statistics", response_model=Dict)
async def get_issue_statistics(
    quarter_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get statistics about issues"""
    if current_user.employee_role != "facilitator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only facilitators can view issue statistics"
        )
    
    return await IssueService.get_issue_statistics(quarter_id)

# Simple status update endpoint for issues

@router.put("/issues/{issue_id}/status")
async def update_issue_status(
    issue_id: UUID,
    status_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update issue status (employees can update issues assigned to them)"""
    print(f"🔄 PUT /issues/{issue_id}/status called with data: {status_data}")
    
    # Get the issue to verify it exists
    issue = await IssueService.get_issue(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Verify user has permission (facilitator or user who raised the issue)
    # For issues, check if user raised the issue (raised_by_id or raised_by name matches)
    can_update = False
    
    # TEMPORARY: Allow facilitators for testing purposes
    # TODO: Remove this when testing is complete
    if current_user.employee_role == "facilitator":
        print("🧪 TESTING MODE: Allowing facilitator to update issue status")
        can_update = True
    elif current_user.employee_role == "employee":
        # Check if issue was raised by this employee
        issue_dict = issue.model_dump()
        raised_by_id = issue_dict.get('raised_by_id')
        raised_by_name = issue_dict.get('raised_by', '').lower()
        current_user_name = current_user.employee_name.lower()
        
        if (raised_by_id and str(raised_by_id) == str(current_user.employee_id)) or \
           (raised_by_name and raised_by_name == current_user_name):
            can_update = True
    
    if not can_update:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update issues that you raised"
        )
    
    # Validate status
    new_status = status_data.get("status", "open")
    if new_status not in ["open", "resolved", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be one of: open, resolved, pending"
        )
    
    print(f"🔄 Updating issue status: {new_status}")
    
    # Update the status
    update_data = {
        "status": new_status,
        "updated_at": datetime.utcnow()
    }
    
    updated_issue = await IssueService.update_issue(issue_id, update_data)
    if not updated_issue:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update issue status"
        )
    
    print(f"✅ Issue status updated successfully: {updated_issue.model_dump()}")
    return updated_issue
