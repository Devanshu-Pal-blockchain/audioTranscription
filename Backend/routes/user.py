from typing import List, Optional, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.user import User
from service.user_service import UserService
from service.auth_service import get_current_user, admin_required
from service.quarter_service import QuarterService
from service.rock_service import RockService
from service.task_service import TaskService

router = APIRouter()

@router.post("/users", response_model=User)
async def create_user(
    user: User,
    current_user: User = Depends(admin_required)
) -> User:
    """Create a new user (admin only)"""
    created_user = await UserService.create_user(user)
    if not created_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    return created_user

@router.get("/users/me", response_model=User)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current user's profile"""
    return current_user

@router.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> User:
    """Get a user by ID"""
    # Regular users can only view their own profile
    if current_user.employee_role != "admin" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own profile"
        )
    user = await UserService.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.get("/users", response_model=List[User])
async def list_users(
    role: Optional[str] = None,
    current_user: User = Depends(admin_required)
) -> List[User]:
    """List all users, optionally filtered by role (admin only)"""
    return await UserService.get_users(role)

@router.put("/users/{user_id}", response_model=User)
async def update_user(
    user_id: UUID,
    user_update: User,
    current_user: User = Depends(get_current_user)
) -> User:
    """Update a user"""
    # Regular users can only update their own profile
    if current_user.employee_role != "admin" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own profile"
        )
    # Only admins can change roles
    if (current_user.employee_role != "admin" and 
        user_update.employee_role != current_user.employee_role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change your own role"
        )
    updated_user = await UserService.update_user(user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return updated_user

@router.put("/users/{user_id}/password")
async def update_password(
    user_id: UUID,
    new_password: str,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Update a user's password"""
    # Regular users can only update their own password
    if current_user.employee_role != "admin" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own password"
        )
    success = await UserService.update_password(user_id, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "Password updated successfully"}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(admin_required)
) -> dict:
    """Delete a user (admin only)"""
    # Prevent self-deletion
    if current_user.employee_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    success = await UserService.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return {"message": "User deleted successfully"}

# Combined Operations
@router.get("/users/{user_id}/dashboard", response_model=Dict)
async def get_user_dashboard(
    user_id: UUID,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get user's dashboard data including quarters, rocks, and tasks"""
    # Regular users can only view their own dashboard
    if current_user.employee_role != "admin" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own dashboard"
        )
    
    # Get user details
    user = await UserService.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's quarters
    quarters = await QuarterService.get_quarters_by_participant(user_id)
    
    # Get rocks and tasks for each quarter
    quarters_data = []
    total_rocks = 0
    total_tasks = 0
    
    for quarter in quarters:
        if not quarter.quarter_id:
            continue
            
        # Get rocks for this quarter
        rocks = await RockService.get_rocks_by_quarter(quarter.quarter_id)
        if current_user.employee_role != "admin":
            rocks = [rock for rock in rocks if str(rock.assigned_to_id) == str(user_id)]
        
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
        quarters_data.append(quarter_dict)
        
        total_rocks += len(rocks_with_tasks)
        total_tasks += quarter_tasks
    
    return {
        "user": user.model_dump(),
        "quarters": quarters_data,
        "total_quarters": len(quarters_data),
        "total_rocks": total_rocks,
        "total_tasks": total_tasks
    }

@router.get("/users/{user_id}/current-quarter", response_model=Dict)
async def get_user_current_quarter(
    user_id: UUID,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get user's current quarter data"""
    # Regular users can only view their own data
    if current_user.employee_role != "admin" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own data"
        )
    
    # Get user details
    user = await UserService.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get current quarter
    quarters = await QuarterService.get_quarters_by_participant(user_id)
    current_quarter = None
    for quarter in quarters:
        if quarter.status == 1:  # Active quarter
            current_quarter = quarter
            break
    
    if not current_quarter or not current_quarter.quarter_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active quarter found"
        )
    
    # Get rocks for current quarter
    rocks = await RockService.get_rocks_by_quarter(current_quarter.quarter_id)
    if current_user.employee_role != "admin":
        rocks = [rock for rock in rocks if str(rock.assigned_to_id) == str(user_id)]
    
    # Get tasks for each rock
    rocks_with_tasks = []
    total_tasks = 0
    for rock in rocks:
        tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
        rock_dict = rock.model_dump()
        rock_dict["tasks"] = [task.model_dump() for task in tasks]
        rocks_with_tasks.append(rock_dict)
        total_tasks += len(tasks)
    
    quarter_dict = current_quarter.model_dump()
    quarter_dict["rocks"] = rocks_with_tasks
    quarter_dict["total_rocks"] = len(rocks_with_tasks)
    quarter_dict["total_tasks"] = total_tasks
    
    return {
        "user": user.model_dump(),
        "current_quarter": quarter_dict
    }

@router.get("/users/{user_id}/week/{week}", response_model=Dict)
async def get_user_week_tasks(
    user_id: UUID,
    week: int,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get user's tasks for a specific week"""
    # Regular users can only view their own data
    if current_user.employee_role != "admin" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own data"
        )
    
    # Get user details
    user = await UserService.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get current quarter
    quarters = await QuarterService.get_quarters_by_participant(user_id)
    current_quarter = None
    for quarter in quarters:
        if quarter.status == 1:  # Active quarter
            current_quarter = quarter
            break
    
    if not current_quarter or not current_quarter.quarter_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active quarter found"
        )
    
    # Validate week number
    if week < 1 or week > current_quarter.weeks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Week must be between 1 and {current_quarter.weeks}"
        )
    
    # Get rocks for current quarter
    rocks = await RockService.get_rocks_by_quarter(current_quarter.quarter_id)
    if current_user.employee_role != "admin":
        rocks = [rock for rock in rocks if str(rock.assigned_to_id) == str(user_id)]
    
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
    
    return {
        "user": user.model_dump(),
        "quarter": current_quarter.model_dump(),
        "week": week,
        "rocks": rocks_with_tasks,
        "total_rocks": len(rocks_with_tasks),
        "total_tasks": total_tasks
    }

@router.get("/users/{user_id}/rocks/all", response_model=Dict)
async def get_user_rocks_with_tasks(
    user_id: UUID,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get all rocks assigned to a user with their tasks"""
    # Regular users can only view their own data
    if current_user.employee_role != "admin" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own data"
        )
    
    # Get user details
    user = await UserService.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's rocks
    rocks = await RockService.get_rocks_by_user(user_id)
    
    # Get tasks for each rock
    rocks_with_tasks = []
    total_tasks = 0
    
    for rock in rocks:
        tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
        rock_dict = rock.model_dump()
        rock_dict["tasks"] = [task.model_dump() for task in tasks]
        rocks_with_tasks.append(rock_dict)
        total_tasks += len(tasks)
    
    return {
        "user": user.model_dump(),
        "rocks": rocks_with_tasks,
        "total_rocks": len(rocks_with_tasks),
        "total_tasks": total_tasks
    } 