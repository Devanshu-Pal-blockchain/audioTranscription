from typing import List, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.issue import Issue, IssueCreateRequest, IssueUpdateRequest
from models.solution import Solution, SolutionCreateRequest, SolutionUpdateRequest
from models.user import User
from service.issue_service import IssueService
from service.solution_service import SolutionService
from service.ids_analysis_service import IDSAnalysisService
from service.auth_service import get_current_user, admin_required

router = APIRouter()

# Issue endpoints
@router.post("/issues", response_model=Issue)
async def create_issue(
    issue_request: IssueCreateRequest,
    current_user: User = Depends(get_current_user)
) -> Issue:
    """Create a new issue"""
    issue = Issue.from_create_request(issue_request, current_user.employee_id)
    return await IssueService.create_issue(issue)

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
    
    # Check access - users can view issues they created, are assigned to, or if they're admin
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != issue.created_by and
        current_user.employee_id != issue.assigned_to and
        current_user.employee_id not in issue.watchers):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this issue"
        )
    
    return issue

@router.get("/issues", response_model=List[Issue])
async def list_issues(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    category: Optional[str] = Query(None, description="Filter by category"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assignee"),
    meeting_id: Optional[UUID] = Query(None, description="Filter by meeting"),
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    skip: int = Query(0, ge=0, description="Number of issues to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of issues to return"),
    current_user: User = Depends(get_current_user)
) -> List[Issue]:
    """List issues with optional filters"""
    
    # Non-admin users see issues they're involved with
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await IssueService.list_issues(
        status=status_filter,
        priority=priority,
        category=category,
        assigned_to=assigned_to,
        meeting_id=meeting_id,
        quarter_id=quarter_id,
        user_filter=user_filter,
        skip=skip,
        limit=limit
    )

@router.put("/issues/{issue_id}", response_model=Issue)
async def update_issue(
    issue_id: UUID,
    issue_update: IssueUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> Issue:
    """Update an issue"""
    issue = await IssueService.get_issue(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Check permissions - admin, creator, or assignee can update
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != issue.created_by and
        current_user.employee_id != issue.assigned_to):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this issue"
        )
    
    return await IssueService.update_issue(issue_id, issue_update)

@router.delete("/issues/{issue_id}")
async def delete_issue(
    issue_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete an issue"""
    issue = await IssueService.get_issue(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Check permissions - admin or creator can delete
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != issue.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this issue"
        )
    
    success = await IssueService.delete_issue(issue_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete issue"
        )
    return {"message": "Issue deleted successfully"}

# Solution endpoints
@router.post("/solutions", response_model=Solution)
async def create_solution(
    solution_request: SolutionCreateRequest,
    current_user: User = Depends(get_current_user)
) -> Solution:
    """Create a new solution"""
    solution = Solution.from_create_request(solution_request, current_user.employee_id)
    return await SolutionService.create_solution(solution)

@router.get("/solutions/{solution_id}", response_model=Solution)
async def get_solution(
    solution_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Solution:
    """Get a solution by ID"""
    solution = await SolutionService.get_solution(solution_id)
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )
    
    # Check access through related issue
    if solution.issue_id:
        issue = await IssueService.get_issue(solution.issue_id)
        if issue and (current_user.employee_role != "admin" and 
                     current_user.employee_id != issue.created_by and
                     current_user.employee_id != issue.assigned_to and
                     current_user.employee_id not in issue.watchers and
                     current_user.employee_id != solution.created_by):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this solution"
            )
    
    return solution

@router.get("/solutions", response_model=List[Solution])
async def list_solutions(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    issue_id: Optional[UUID] = Query(None, description="Filter by issue"),
    meeting_id: Optional[UUID] = Query(None, description="Filter by meeting"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assignee"),
    skip: int = Query(0, ge=0, description="Number of solutions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of solutions to return"),
    current_user: User = Depends(get_current_user)
) -> List[Solution]:
    """List solutions with optional filters"""
    
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await SolutionService.list_solutions(
        status=status_filter,
        issue_id=issue_id,
        meeting_id=meeting_id,
        assigned_to=assigned_to,
        user_filter=user_filter,
        skip=skip,
        limit=limit
    )

@router.put("/solutions/{solution_id}", response_model=Solution)
async def update_solution(
    solution_id: UUID,
    solution_update: SolutionUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> Solution:
    """Update a solution"""
    solution = await SolutionService.get_solution(solution_id)
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )
    
    # Check permissions - admin, creator, or assignee can update
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != solution.created_by and
        current_user.employee_id != solution.assigned_to):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this solution"
        )
    
    return await SolutionService.update_solution(solution_id, solution_update)

@router.delete("/solutions/{solution_id}")
async def delete_solution(
    solution_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Delete a solution"""
    solution = await SolutionService.get_solution(solution_id)
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )
    
    # Check permissions - admin or creator can delete
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != solution.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this solution"
        )
    
    success = await SolutionService.delete_solution(solution_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete solution"
        )
    return {"message": "Solution deleted successfully"}

# IDS Analysis endpoints
@router.get("/issues/{issue_id}/solutions", response_model=List[Solution])
async def get_issue_solutions(
    issue_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Solution]:
    """Get all solutions for a specific issue"""
    # Check issue access first
    issue = await IssueService.get_issue(issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    if (current_user.employee_role != "admin" and 
        current_user.employee_id != issue.created_by and
        current_user.employee_id != issue.assigned_to and
        current_user.employee_id not in issue.watchers):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this issue"
        )
    
    return await SolutionService.get_solutions_by_issue(issue_id)

@router.post("/meetings/{meeting_id}/analyze-ids")
async def analyze_meeting_ids(
    meeting_id: UUID,
    current_user: User = Depends(admin_required)
) -> Dict[str, str]:
    """Analyze meeting for Issues, Decisions, and Solutions (admin only)"""
    result = await IDSAnalysisService.analyze_meeting_transcript(meeting_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found or transcript not available"
        )
    return {"message": "IDS analysis completed successfully"}

@router.get("/analytics/ids-summary", response_model=Dict)
async def get_ids_summary(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get IDS summary analytics"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    return await IDSAnalysisService.get_ids_summary(quarter_id, user_filter)

@router.get("/analytics/issue-trends", response_model=Dict)
async def get_issue_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get issue trends over time"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    return await IDSAnalysisService.get_issue_trends(days, user_filter)
