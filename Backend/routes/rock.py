from typing import List, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.rock import Rock
from models.task import Task
from service.rock_service import RockService
from service.task_service import TaskService
from service.auth_service import get_current_user, facilitator_required
from models.user import User

router = APIRouter()

@router.post("/rocks", response_model=Rock)
async def create_rock(
    rock: Rock,
    current_user: User = Depends(facilitator_required)
) -> Rock:
    """Create a new rock (facilitator only)"""
    return await RockService.create_rock(rock)

@router.get("/rocks/{rock_id}", response_model=Rock)
async def get_rock(
    rock_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Rock:
    """Get a rock by ID"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    # Check access
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this rock"
        )
    
    return rock

@router.get("/rocks/quarter/{quarter_id}", response_model=List[Rock])
async def list_quarter_rocks(
    quarter_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Rock]:
    """List all rocks for a specific quarter"""
    if current_user.employee_role == "facilitator":
        return await RockService.get_rocks_by_quarter(quarter_id)
    
    # For regular users, filter by assignment
    all_rocks = await RockService.get_rocks_by_quarter(quarter_id)
    return [rock for rock in all_rocks if str(rock.assigned_to_id) == str(current_user.employee_id)]

@router.get("/rocks/user/{user_id}", response_model=List[Rock])
async def list_user_rocks(
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Rock]:
    """List all rocks assigned to a specific user"""
    # Users can only view their own rocks unless they're facilitator
    if current_user.employee_role != "facilitator" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own rocks"
        )
    return await RockService.get_rocks_by_user(user_id)

@router.put("/rocks/{rock_id}", response_model=Rock)
async def update_rock(
    rock_id: UUID,
    rock_update: Rock,
    current_user: User = Depends(facilitator_required)
) -> Rock:
    """Update a rock (facilitator only)"""
    rock = await RockService.update_rock(rock_id, rock_update)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    return rock

@router.delete("/rocks/{rock_id}")
async def delete_rock(
    rock_id: UUID,
    current_user: User = Depends(facilitator_required)
) -> dict:
    """Delete a rock (facilitator only)"""
    success = await RockService.delete_rock(rock_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    return {"message": "Rock deleted successfully"}

# Combined Operations
@router.get("/rocks/{rock_id}/tasks", response_model=Dict)
async def get_rock_with_tasks(
    rock_id: UUID,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get a rock with all its tasks"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    # Check access
    if current_user.employee_role != "admin" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this rock"
        )
    
    tasks = await TaskService.get_tasks_by_rock(rock_id, include_comments)
    result = rock.model_dump()
    result["tasks"] = [task.model_dump() for task in tasks]
    return result

@router.post("/rocks/{rock_id}/tasks", response_model=Dict)
async def create_rock_tasks(
    rock_id: UUID,
    tasks: List[Task],
    current_user: User = Depends(admin_required)
) -> Dict:
    """Create new tasks for a rock (admin only)"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    created_tasks = []
    for task in tasks:
        task.rock_id = rock_id
        created_task = await TaskService.create_task(task)
        created_tasks.append(created_task)
    
    result = rock.model_dump()
    result["tasks"] = [task.model_dump() for task in created_tasks]
    return result

@router.put("/rocks/{rock_id}/tasks", response_model=Dict)
async def update_rock_tasks(
    rock_id: UUID,
    tasks: List[Task],
    current_user: User = Depends(admin_required)
) -> Dict:
    """Update tasks for a rock (admin only)"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    updated_tasks = []
    for task in tasks:
        if task.rock_id != rock_id:
            continue
        updated_task = await TaskService.update_task(task.task_id, task)
        if updated_task:
            updated_tasks.append(updated_task)
    
    result = rock.model_dump()
    result["tasks"] = [task.model_dump() for task in updated_tasks]
    return result

@router.delete("/rocks/{rock_id}/tasks")
async def delete_rock_tasks(
    rock_id: UUID,
    current_user: User = Depends(admin_required)
) -> dict:
    """Delete all tasks for a rock (admin only)"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    tasks = await TaskService.get_tasks_by_rock(rock_id)
    for task in tasks:
        await TaskService.delete_task(task.task_id)
    
    return {"message": "All tasks deleted successfully"}

@router.get("/rocks/quarter/{quarter_id}/all", response_model=Dict)
async def get_quarter_rocks_with_tasks(
    quarter_id: UUID,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get all rocks and their tasks for a quarter"""
    rocks_with_tasks = []
    
    # Get rocks based on user role
    if current_user.employee_role == "admin":
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
    else:
        all_rocks = await RockService.get_rocks_by_quarter(quarter_id)
        rocks = [rock for rock in all_rocks if str(rock.assigned_to_id) == str(current_user.employee_id)]
    
    # Get tasks for each rock
    for rock in rocks:
        tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
        rock_dict = rock.model_dump()
        rock_dict["tasks"] = [task.model_dump() for task in tasks]
        rocks_with_tasks.append(rock_dict)
    
    return {
        "quarter_id": str(quarter_id),
        "rocks": rocks_with_tasks,
        "total_rocks": len(rocks_with_tasks)
    }

@router.put("/rocks/quarter/{quarter_id}/smart-objective/{rock_id}", response_model=Rock)
async def update_smart_objective(
    quarter_id: UUID,
    rock_id: UUID,
    smart_objective: str,
    current_user: User = Depends(admin_required)
) -> Rock:
    """Update a rock's SMART objective (admin only)"""
    rock = await RockService.get_rock_by_quarter(quarter_id, rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found in quarter"
        )
    
    updated_rock = await RockService.update_smart_objective(rock_id, smart_objective)
    if not updated_rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to update SMART objective"
        )
    return updated_rock

@router.post("/rocks/bulk", response_model=Dict)
async def bulk_create_rocks_and_tasks(
    rocks: List[Rock],
    tasks_by_rock: Dict[str, List[Task]],
    current_user: User = Depends(admin_required)
) -> Dict:
    """Bulk create rocks and their tasks (admin only)"""
    created_rocks = []
    created_tasks = []
    
    for rock in rocks:
        created_rock = await RockService.create_rock(rock)
        if not created_rock or not created_rock.rock_id:
            continue
            
        created_rocks.append(created_rock)
        
        # Create tasks for this rock if any
        rock_id_str = str(created_rock.rock_id)
        if rock_id_str in tasks_by_rock:
            for task in tasks_by_rock[rock_id_str]:
                task.rock_id = created_rock.rock_id
                created_task = await TaskService.create_task(task)
                if created_task:
                    created_tasks.append(created_task)
    
    return {
        "rocks": [rock.model_dump() for rock in created_rocks],
        "tasks": [task.model_dump() for task in created_tasks],
        "total_rocks": len(created_rocks),
        "total_tasks": len(created_tasks)
    }

# VTO-specific endpoints

@router.get("/rocks/type/{rock_type}", response_model=List[Rock])
async def list_rocks_by_type(
    rock_type: str,
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    current_user: User = Depends(get_current_user)
) -> List[Rock]:
    """List rocks by type (annual, company, individual)"""
    # Validate rock type
    valid_types = ["annual", "company", "individual"]
    if rock_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid rock type. Must be one of: {', '.join(valid_types)}"
        )
    
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    return await RockService.get_rocks_by_type(rock_type, quarter_id, user_filter)

@router.get("/rocks/{rock_id}/progress", response_model=Dict)
async def get_rock_progress(
    rock_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get detailed progress information for a rock"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    # Check access
    if current_user.employee_role != "admin" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this rock"
        )
    
    return await RockService.get_rock_progress(rock_id)

@router.post("/rocks/{rock_id}/update-progress")
async def update_rock_progress(
    rock_id: UUID,
    percentage: float = Query(..., ge=0.0, le=100.0, description="Progress percentage"),
    notes: Optional[str] = Query(None, description="Progress notes"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Update rock progress percentage"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    # Check permissions
    if (current_user.employee_role != "admin" and 
        str(rock.assigned_to_id) != str(current_user.employee_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this rock"
        )
    
    success = await RockService.update_rock_progress(rock_id, percentage, notes, current_user.employee_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update rock progress"
        )
    return {"message": "Rock progress updated successfully"}

@router.get("/rocks/{rock_id}/milestones", response_model=List[Dict])
async def get_rock_milestones(
    rock_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """Get milestones associated with a rock"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    # Check access
    if current_user.employee_role != "admin" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this rock"
        )
    
    return await RockService.get_rock_milestones(rock_id)

@router.get("/rocks/analytics/completion-rate", response_model=Dict)
async def get_rock_completion_analytics(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    rock_type: Optional[str] = Query(None, description="Filter by rock type"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get rock completion rate analytics"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    return await RockService.get_completion_analytics(quarter_id, rock_type, user_filter)

@router.get("/rocks/analytics/at-risk", response_model=List[Dict])
async def get_at_risk_rocks(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """Get rocks that are at risk of not being completed"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    return await RockService.get_at_risk_rocks(quarter_id, user_filter)

@router.get("/users/{user_id}/rocks/summary", response_model=Dict)
async def get_user_rocks_summary(
    user_id: UUID,
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get summary of all rock types for a user"""
    # Users can only view their own summary unless they're admin
    if current_user.employee_role != "admin" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own rock summary"
        )
    
    return await RockService.get_user_rocks_summary(user_id, quarter_id)

@router.post("/rocks/{rock_id}/assign-milestone")
async def assign_milestone_to_rock(
    rock_id: UUID,
    milestone_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Assign an existing milestone to a rock"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    # Check permissions
    if (current_user.employee_role != "admin" and 
        str(rock.assigned_to_id) != str(current_user.employee_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this rock"
        )
    
    success = await RockService.assign_milestone(rock_id, milestone_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign milestone to rock"
        )
    return {"message": "Milestone assigned to rock successfully"}

@router.delete("/rocks/{rock_id}/milestones/{milestone_id}")
async def remove_milestone_from_rock(
    rock_id: UUID,
    milestone_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Remove a milestone from a rock"""
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    # Check permissions
    if (current_user.employee_role != "admin" and 
        str(rock.assigned_to_id) != str(current_user.employee_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this rock"
        )
    
    success = await RockService.remove_milestone(rock_id, milestone_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove milestone from rock"
        )
    return {"message": "Milestone removed from rock successfully"}