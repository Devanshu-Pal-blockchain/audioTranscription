from typing import List, Optional, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.quarter import Quarter
from models.rock import Rock
from models.task import Task
from service.quarter_service import QuarterService
from service.rock_service import RockService
from service.task_service import TaskService
from service.todo_service import TodoService
from service.issue_service import IssueService
from service.auth_service import get_current_user, facilitator_required
from models.user import User
from pydantic import BaseModel, Field

router = APIRouter()

@router.get("/quarters/user", response_model=List[Dict])
async def get_user_quarters(
    current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """Get all quarters where the current user is a participant"""
    quarters = await QuarterService.get_quarters_by_participant(current_user.employee_id)
    if not quarters:
        return []
    
    # Return simplified quarter data with just id and name info
    return [
        {
            "quarter_id": str(quarter.id),
            "quarter_name": quarter.quarter,
            "year": quarter.year,
            "title": quarter.title,
            "full_name": f"{quarter.quarter} {quarter.year} - {quarter.title}"
        }
        for quarter in quarters
    ]

@router.get("/quarters/{quarter_id}/data", response_model=Dict)
async def get_quarter_data(
    quarter_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get comprehensive data for a specific quarter (rocks, todos, issues, milestones)"""
    # Verify user has access to this quarter
    quarter = await QuarterService.get_quarter(quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    
    # Check if user is participant in this quarter
    if current_user.employee_id not in quarter.participants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this quarter"
        )
    
    # Fetch all related data for this quarter
    rocks = await RockService.get_rocks_by_quarter(quarter_id)
    todos = await TodoService.get_todos_by_quarter(quarter_id)
    issues = await IssueService.get_issues_by_quarter(quarter_id)
    
    return {
        "quarter": quarter.model_dump(),
        "rocks": [rock.model_dump() for rock in rocks],
        "todos": [todo.model_dump() for todo in todos],
        "issues": [issue.model_dump() for issue in issues]
    }

# Field update models
class WeeksUpdate(BaseModel):
    weeks: int = Field(gt=0, description="Number of weeks in quarter")

class YearUpdate(BaseModel):
    year: int = Field(gt=1900, lt=10000, description="Year of the quarter")

class TitleUpdate(BaseModel):
    title: str = Field(min_length=1, description="Quarter title")

class DescriptionUpdate(BaseModel):
    description: str = Field(description="Quarter description")

class StatusUpdate(BaseModel):
    status: int = Field(ge=0, le=1, description="Quarter status (0 = draft, 1 = saved)")

@router.post("/quarters", response_model=Quarter)
async def create_quarter(
    quarter: Quarter,
    current_user: User = Depends(facilitator_required)
) -> Quarter:
    """Create a new quarter (facilitator only)"""
    return await QuarterService.create_quarter(quarter)

@router.get("/quarters/{quarter_id}", response_model=Quarter)
async def get_quarter(
    quarter_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Quarter:
    """Get a quarter by ID"""
    quarter = await QuarterService.get_quarter(quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return quarter

@router.get("/quarters", response_model=List[Quarter])
async def list_quarters(
    year: Optional[int] = None,
    status: Optional[int] = None,
    current_user: User = Depends(get_current_user)
) -> List[Quarter]:
    """List all quarters, optionally filtered by year and status"""
    return await QuarterService.get_quarters(year, status)

@router.put("/quarters/{quarter_id}", response_model=Quarter)
async def update_quarter(
    quarter_id: UUID,
    quarter_update: Quarter,
    current_user: User = Depends(facilitator_required)
) -> Quarter:
    """Update a quarter (facilitator only)"""
    quarter = await QuarterService.update_quarter(quarter_id, quarter_update)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return quarter

@router.delete("/quarters/{quarter_id}")
async def delete_quarter(
    quarter_id: UUID,
    current_user: User = Depends(facilitator_required)
) -> dict:
    """Delete a quarter and its associated rocks (facilitator only)"""
    success = await QuarterService.delete_quarter(quarter_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return {"message": "Quarter and associated rocks deleted successfully"}

@router.put("/quarters/{quarter_id}/weeks", response_model=Quarter)
async def update_quarter_weeks(
    quarter_id: UUID,
    update: WeeksUpdate,
    current_user: User = Depends(facilitator_required)
) -> Quarter:
    """Update quarter weeks (facilitator only)"""
    quarter = await QuarterService.update_quarter_field(quarter_id, "weeks", update.weeks)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return quarter

@router.put("/quarters/{quarter_id}/year", response_model=Quarter)
async def update_quarter_year(
    quarter_id: UUID,
    update: YearUpdate,
    current_user: User = Depends(facilitator_required)
) -> Quarter:
    """Update quarter year (facilitator only)"""
    quarter = await QuarterService.update_quarter_field(quarter_id, "year", update.year)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return quarter

@router.put("/quarters/{quarter_id}/title", response_model=Quarter)
async def update_quarter_title(
    quarter_id: UUID,
    update: TitleUpdate,
    current_user: User = Depends(facilitator_required)
) -> Quarter:
    """Update quarter title (facilitator only)"""
    quarter = await QuarterService.update_quarter_field(quarter_id, "title", update.title)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return quarter

@router.put("/quarters/{quarter_id}/description", response_model=Quarter)
async def update_quarter_description(
    quarter_id: UUID,
    update: DescriptionUpdate,
    current_user: User = Depends(facilitator_required)
) -> Quarter:
    """Update quarter description (facilitator only)"""
    quarter = await QuarterService.update_quarter_field(quarter_id, "description", update.description)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return quarter

@router.put("/quarters/{quarter_id}/status", response_model=Quarter)
async def update_quarter_status(
    quarter_id: UUID,
    update: StatusUpdate,
    current_user: User = Depends(facilitator_required)
) -> Quarter:
    """Update quarter status (facilitator only)"""
    quarter = await QuarterService.update_quarter_field(quarter_id, "status", update.status)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return quarter

@router.get("/quarters/status/{status}", response_model=List[Quarter])
async def list_quarters_by_status(
    status: int,
    current_user: User = Depends(get_current_user)
) -> List[Quarter]:
    """List all quarters with a specific status"""
    if status not in [0, 1]:
        raise HTTPException(
            status_code=400,
            detail="Status must be 0 (draft) or 1 (saved)"
        )
    return await QuarterService.get_quarters_by_status(status)

@router.post("/quarters/{quarter_id}/participants/{user_id}", response_model=Quarter)
async def add_participant(
    quarter_id: UUID,
    user_id: UUID,
    current_user: User = Depends(facilitator_required)
) -> Quarter:
    """Add a participant to a quarter (facilitator only)"""
    quarter = await QuarterService.add_participant(quarter_id, user_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return quarter

@router.delete("/quarters/{quarter_id}/participants/{user_id}", response_model=Quarter)
async def remove_participant(
    quarter_id: UUID,
    user_id: UUID,
    current_user: User = Depends(facilitator_required)
) -> Quarter:
    """Remove a participant from a quarter (facilitator only)"""
    quarter = await QuarterService.remove_participant(quarter_id, user_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    return quarter

@router.get("/quarters/participant/{user_id}", response_model=List[Quarter])
async def get_user_quarters(
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Quarter]:
    """Get all quarters where a user is a participant"""
    # Users can only view their own quarters unless they're facilitator
    if current_user.employee_role != "facilitator" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own quarters"
        )
    return await QuarterService.get_quarters_by_participant(user_id)

@router.get("/quarters/{quarter_id}/all", response_model=Dict)
async def get_quarter_with_rocks_and_tasks(
    quarter_id: UUID,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get a quarter with all its rocks, tasks, todos, and issues"""
    # Verify quarter exists
    quarter = await QuarterService.get_quarter(quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    
    # Get rocks based on user role
    if current_user.employee_role == "facilitator":
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
    else:
        all_rocks = await RockService.get_rocks_by_quarter(quarter_id)
        rocks = [rock for rock in all_rocks if str(rock.assigned_to_id) == str(current_user.employee_id)]
    
    # Get tasks for each rock
    rocks_with_tasks = []
    total_tasks = 0
    for rock in rocks:
        tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
        rock_dict = rock.model_dump()
        rock_dict["tasks"] = [task.model_dump() for task in tasks]
        rocks_with_tasks.append(rock_dict)
        total_tasks += len(tasks)
    
    # Get todos for the quarter
    try:
        todos = await TodoService.get_todos_by_quarter(quarter_id)
        todos_list = [todo.model_dump() for todo in todos]
        print(f"Found {len(todos_list)} todos for quarter {quarter_id}")
    except Exception as e:
        print(f"Error fetching todos for quarter {quarter_id}: {e}")
        todos_list = []
    
    # Get issues for the quarter
    try:
        issues = await IssueService.get_issues_by_quarter(quarter_id)
        issues_list = [issue.model_dump() for issue in issues]
        print(f"Found {len(issues_list)} issues for quarter {quarter_id}")
    except Exception as e:
        print(f"Error fetching issues for quarter {quarter_id}: {e}")
        issues_list = []
    
    result = quarter.model_dump()
    result["rocks"] = rocks_with_tasks
    result["todos"] = todos_list
    result["issues"] = issues_list
    result["total_rocks"] = len(rocks_with_tasks)
    result["total_tasks"] = total_tasks
    result["total_todos"] = len(todos_list)
    result["total_issues"] = len(issues_list)
    return result

@router.get("/quarters/{quarter_id}/week/{week}", response_model=Dict)
async def get_quarter_week_data(
    quarter_id: UUID,
    week: int,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get all data for a specific week in a quarter"""
    # Verify quarter exists
    quarter = await QuarterService.get_quarter(quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    
    # Validate week number
    if week < 1 or week > quarter.weeks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Week must be between 1 and {quarter.weeks}"
        )
    
    # Get rocks based on user role
    if current_user.employee_role == "facilitator":
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
    else:
        all_rocks = await RockService.get_rocks_by_quarter(quarter_id)
        rocks = [rock for rock in all_rocks if str(rock.assigned_to_id) == str(current_user.employee_id)]
    
    # Get tasks for each rock for the specified week
    rocks_with_tasks = []
    total_tasks = 0
    for rock in rocks:
        tasks = await TaskService.get_tasks_by_week(rock.rock_id, week)
        if include_comments:
            task_details = []
            for task in tasks:
                task_with_comments = await TaskService.get_task(task.task_id)
                if task_with_comments:
                    task_details.append(task_with_comments)
            tasks = task_details
        rock_dict = rock.model_dump()
        rock_dict["tasks"] = [task.model_dump() for task in tasks]
        rocks_with_tasks.append(rock_dict)
        total_tasks += len(tasks)
    
    result = quarter.model_dump()
    result["week"] = week
    result["rocks"] = rocks_with_tasks
    result["total_rocks"] = len(rocks_with_tasks)
    result["total_tasks"] = total_tasks
    return result

@router.get("/quarters/user/{user_id}/all", response_model=Dict)
async def get_user_quarters_with_data(
    user_id: UUID,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get all quarters with rocks and tasks for a user"""
    # Users can only view their own data unless they're facilitator
    if current_user.employee_role != "facilitator" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own data"
        )
    
    # Get all quarters for the user
    quarters = await QuarterService.get_quarters_by_participant(user_id)
    
    # Get rocks and tasks for each quarter
    quarters_with_data = []
    total_rocks = 0
    total_tasks = 0
    
    for quarter in quarters:
        if not quarter.id:
            continue
            
        # Get rocks for this quarter
        if current_user.employee_role == "facilitator":
            rocks = await RockService.get_rocks_by_quarter(quarter.id)
        else:
            all_rocks = await RockService.get_rocks_by_quarter(quarter.id)
            rocks = [rock for rock in all_rocks if str(rock.assigned_to_id) == str(current_user.employee_id)]
        
        # Get tasks for each rock
        rocks_with_tasks = []
        quarter_tasks = 0
        for rock in rocks:
            tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
            rock_dict = rock.model_dump()
            rock_dict["tasks"] = [task.model_dump() for task in tasks]
            rocks_with_tasks.append(rock_dict)
            quarter_tasks += len(tasks)
        
        quarter_dict = quarter.model_dump()
        quarter_dict["rocks"] = rocks_with_tasks
        quarter_dict["total_rocks"] = len(rocks_with_tasks)
        quarter_dict["total_tasks"] = quarter_tasks
        quarters_with_data.append(quarter_dict)
        
        total_rocks += len(rocks_with_tasks)
        total_tasks += quarter_tasks
    
    return {
        "user_id": str(user_id),
        "quarters": quarters_with_data,
        "total_quarters": len(quarters_with_data),
        "total_rocks": total_rocks,
        "total_tasks": total_tasks
    }

@router.post("/quarters/{quarter_id}/bulk", response_model=Dict)
async def bulk_create_quarter_data(
    quarter_id: UUID,
    rocks: List[Rock],
    tasks_by_rock: Dict[str, List[Task]],
    current_user: User = Depends(facilitator_required)
) -> Dict:
    """Bulk create rocks and tasks for a quarter (facilitator only)"""
    # Verify quarter exists
    quarter = await QuarterService.get_quarter(quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    
    created_rocks = []
    created_tasks = []
    failed_rocks = []
    failed_tasks = []
    
    # Create rocks
    for rock in rocks:
        rock.quarter_id = quarter_id
        try:
            created_rock = await RockService.create_rock(rock)
            created_rocks.append(created_rock.model_dump())
            
            # Create tasks for this rock if provided
            rock_tasks = tasks_by_rock.get(str(rock.rock_id), [])
            for task in rock_tasks:
                task.rock_id = created_rock.rock_id
                try:
                    created_task = await TaskService.create_task(task)
                    created_tasks.append(created_task.model_dump())
                except Exception as e:
                    failed_tasks.append({
                        "task": task.model_dump(),
                        "error": str(e)
                    })
        except Exception as e:
            failed_rocks.append({
                "rock": rock.model_dump(),
                "error": str(e)
            })
    
    return {
        "quarter_id": str(quarter_id),
        "created_rocks": created_rocks,
        "created_tasks": created_tasks,
        "failed_rocks": failed_rocks,
        "failed_tasks": failed_tasks,
        "total_rocks_created": len(created_rocks),
        "total_tasks_created": len(created_tasks)
    } 
