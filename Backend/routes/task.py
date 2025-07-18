from typing import List, Optional, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.task import Task, Comment
from service.task_service import TaskService
from service.rock_service import RockService
from service.quarter_service import QuarterService
from service.auth_service import get_current_user, facilitator_required
from models.user import User
from datetime import datetime

router = APIRouter()

@router.post("/tasks", response_model=Task)
async def create_task(
    task: Task,
    current_user: User = Depends(get_current_user)
) -> Task:
    """Create a new task"""
    # Verify user has access to the rock
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only create tasks for rocks assigned to you"
        )
    created_task = await TaskService.create_task(task)
    if not created_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )
    return created_task

@router.get("/tasks/{task_id}", response_model=Task)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Task:
    """Get a task by ID"""
    task = await TaskService.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    # Verify user has access to the rock
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated rock not found"
        )
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view tasks for rocks assigned to you"
        )
    return task

@router.get("/tasks/rock/{rock_id}", response_model=List[Task])
async def list_rock_tasks(
    rock_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Task]:
    """List all tasks for a specific rock"""
    # Verify user has access to the rock
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view tasks for rocks assigned to you"
        )
    return await TaskService.get_tasks_by_rock(rock_id)

@router.get("/tasks/rock/{rock_id}/week/{week}", response_model=List[Task])
async def list_week_tasks(
    rock_id: UUID,
    week: int,
    current_user: User = Depends(get_current_user)
) -> List[Task]:
    """List all tasks for a specific rock and week"""
    # Verify user has access to the rock
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view tasks for rocks assigned to you"
        )
    return await TaskService.get_tasks_by_week(rock_id, week)

@router.put("/tasks/{task_id}", response_model=Task)
async def update_task(
    task_id: UUID,
    task_update: Task,
    current_user: User = Depends(get_current_user)
) -> Task:
    """Update a task"""
    # Verify task exists
    task = await TaskService.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    # Verify user has access to the rock
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated rock not found"
        )
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update tasks for rocks assigned to you"
        )
    updated_task = await TaskService.update_task(task_id, task_update)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )
    return updated_task

@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Delete a task"""
    # Verify task exists
    task = await TaskService.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    # Verify user has access to the rock
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated rock not found"
        )
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete tasks for rocks assigned to you"
        )
    success = await TaskService.delete_task(task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )
    return {"message": "Task deleted successfully"}

@router.post("/tasks/{task_id}/subtasks/{key}", response_model=Task)
async def add_subtask(
    task_id: UUID,
    key: str,
    content: str,
    current_user: User = Depends(get_current_user)
) -> Task:
    """Add a subtask to a task"""
    # Verify task exists and user has access
    task = await TaskService.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated rock not found"
        )
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only add subtasks to tasks for rocks assigned to you"
        )
    updated_task = await TaskService.add_subtask(task_id, key, content)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add subtask"
        )
    return updated_task

@router.delete("/tasks/{task_id}/subtasks/{key}", response_model=Task)
async def remove_subtask(
    task_id: UUID,
    key: str,
    current_user: User = Depends(get_current_user)
) -> Task:
    """Remove a subtask from a task"""
    # Verify task exists and user has access
    task = await TaskService.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated rock not found"
        )
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only remove subtasks from tasks for rocks assigned to you"
        )
    updated_task = await TaskService.remove_subtask(task_id, key)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove subtask"
        )
    return updated_task

@router.post("/tasks/{task_id}/comments", response_model=Task)
async def add_comment(
    task_id: UUID,
    comment: Comment,
    current_user: User = Depends(get_current_user)
) -> Task:
    """Add a comment to a task"""
    # Verify task exists
    task = await TaskService.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Verify user has access to the rock
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated rock not found"
        )
    
    # Only facilitators can add facilitator comments
    if comment.is_facilitator_comment and current_user.employee_role != "facilitator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only facilitators can add facilitator comments"
        )
    
    # Regular users can only comment on their own tasks
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only comment on tasks assigned to you"
        )
    
    # Set comment metadata
    comment.commented_by = current_user.employee_name
    comment.created_at = datetime.utcnow()
    
    updated_task = await TaskService.add_comment(task_id, comment)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add comment"
        )
    return updated_task

@router.delete("/tasks/{task_id}/comments/{comment_id}", response_model=Task)
async def remove_comment(
    task_id: UUID,
    comment_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Task:
    """Remove a comment from a task"""
    # Verify task exists
    task = await TaskService.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Verify user has access to the rock
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated rock not found"
        )
    
    # Find the comment
    comment = None
    for c in task.comments:
        if c.comment_id == comment_id:
            comment = c
            break
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Only facilitators can delete facilitator comments
    if comment.is_facilitator_comment and current_user.employee_role != "facilitator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only facilitators can delete facilitator comments"
        )
    
    # Regular users can only delete their own comments
    if current_user.employee_role != "facilitator":
        if comment.commented_by != current_user.employee_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only delete your own comments"
            )
        if str(rock.assigned_to_id) != str(current_user.employee_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only delete comments on tasks assigned to you"
            )
    
    updated_task = await TaskService.remove_comment(task_id, comment_id)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove comment"
        )
    return updated_task

@router.put("/tasks/{task_id}/comments/{comment_id}", response_model=Task)
async def update_comment(
    task_id: UUID,
    comment_id: UUID,
    content: str,
    current_user: User = Depends(get_current_user)
) -> Task:
    """Update a comment on a task"""
    # Verify task exists
    task = await TaskService.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Verify user has access to the rock
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated rock not found"
        )
    
    # Find the comment
    comment = None
    for c in task.comments:
        if c.comment_id == comment_id:
            comment = c
            break
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    # Only facilitators can update facilitator comments
    if comment.is_facilitator_comment and current_user.employee_role != "facilitator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only facilitators can update facilitator comments"
        )
    
    # Regular users can only update their own comments
    if current_user.employee_role != "facilitator":
        if comment.commented_by != current_user.employee_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update your own comments"
            )
        if str(rock.assigned_to_id) != str(current_user.employee_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update comments on tasks assigned to you"
            )
    
    updated_task = await TaskService.update_comment(task_id, comment_id, content)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update comment"
        )
    return updated_task

@router.get("/tasks/quarter/{quarter_id}/all", response_model=Dict)
async def get_quarter_tasks(
    quarter_id: UUID,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get all tasks for a quarter, organized by rock"""
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
    tasks_by_rock = {}
    total_tasks = 0
    for rock in rocks:
        tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
        tasks_by_rock[str(rock.rock_id)] = {
            "rock": rock.model_dump(),
            "tasks": [task.model_dump() for task in tasks]
        }
        total_tasks += len(tasks)
    
    return {
        "quarter_id": str(quarter_id),
        "tasks_by_rock": tasks_by_rock,
        "total_tasks": total_tasks
    }

@router.get("/tasks/quarter/{quarter_id}/week/{week}", response_model=Dict)
async def get_quarter_week_tasks(
    quarter_id: UUID,
    week: int,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get all tasks for a specific week in a quarter"""
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
    
    # Get tasks for each rock for the specified week
    tasks_by_rock = {}
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
        tasks_by_rock[str(rock.rock_id)] = {
            "rock": rock.model_dump(),
            "tasks": [task.model_dump() for task in tasks]
        }
        total_tasks += len(tasks)
    
    return {
        "quarter_id": str(quarter_id),
        "week": week,
        "tasks_by_rock": tasks_by_rock,
        "total_tasks": total_tasks
    }

@router.put("/tasks/bulk", response_model=Dict)
async def bulk_update_tasks(
    tasks: List[Task],
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Bulk update multiple tasks"""
    updated_tasks = []
    failed_tasks = []
    
    for task in tasks:
        # Verify task exists
        existing_task = await TaskService.get_task(task.task_id)
        if not existing_task:
            failed_tasks.append({"task_id": str(task.task_id), "error": "Task not found"})
            continue
        
        # Verify user has access to the rock
        rock = await RockService.get_rock(existing_task.rock_id)
        if not rock:
            failed_tasks.append({"task_id": str(task.task_id), "error": "Associated rock not found"})
            continue
        
        if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
            failed_tasks.append({"task_id": str(task.task_id), "error": "Not authorized to update this task"})
            continue
        
        # Update task
        updated_task = await TaskService.update_task(task.task_id, task)
        if updated_task:
            updated_tasks.append(updated_task.model_dump())
        else:
            failed_tasks.append({"task_id": str(task.task_id), "error": "Failed to update task"})
    
    return {
        "success": len(updated_tasks),
        "failed": len(failed_tasks),
        "updated_tasks": updated_tasks,
        "failed_tasks": failed_tasks
    }

@router.post("/tasks/bulk", response_model=Dict)
async def bulk_create_tasks(
    tasks: List[Task],
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Bulk create multiple tasks"""
    created_tasks = []
    failed_tasks = []
    
    for task in tasks:
        # Verify user has access to the rock
        rock = await RockService.get_rock(task.rock_id)
        if not rock:
            failed_tasks.append({"task": task.model_dump(), "error": "Rock not found"})
            continue
        
        if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
            failed_tasks.append({"task": task.model_dump(), "error": "Not authorized to create tasks for this rock"})
            continue
        
        # Create task
        created_task = await TaskService.create_task(task)
        if created_task:
            created_tasks.append(created_task.model_dump())
        else:
            failed_tasks.append({"task": task.model_dump(), "error": "Failed to create task"})
    
    return {
        "success": len(created_tasks),
        "failed": len(failed_tasks),
        "created_tasks": created_tasks,
        "failed_tasks": failed_tasks
    }

@router.delete("/tasks/bulk", response_model=Dict)
async def bulk_delete_tasks(
    task_ids: List[UUID],
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Bulk delete multiple tasks"""
    deleted_tasks = []
    failed_tasks = []
    
    for task_id in task_ids:
        # Verify task exists
        task = await TaskService.get_task(task_id)
        if not task:
            failed_tasks.append({"task_id": str(task_id), "error": "Task not found"})
            continue
        
        # Verify user has access to the rock
        rock = await RockService.get_rock(task.rock_id)
        if not rock:
            failed_tasks.append({"task_id": str(task_id), "error": "Associated rock not found"})
            continue
        
        if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
            failed_tasks.append({"task_id": str(task_id), "error": "Not authorized to delete this task"})
            continue
        
        # Delete task
        success = await TaskService.delete_task(task_id)
        if success:
            deleted_tasks.append(str(task_id))
        else:
            failed_tasks.append({"task_id": str(task_id), "error": "Failed to delete task"})
    
    return {
        "success": len(deleted_tasks),
        "failed": len(failed_tasks),
        "deleted_tasks": deleted_tasks,
        "failed_tasks": failed_tasks
    }

@router.get("/tasks/user/{user_id}/all", response_model=Dict)
async def get_user_tasks(
    user_id: UUID,
    include_comments: bool = Query(False, description="Include task comments"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get all tasks for a user across all rocks"""
    # Users can only view their own tasks unless they're facilitator
    if current_user.employee_role != "facilitator" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own tasks"
        )
    
    # Get all rocks assigned to the user
    rocks = await RockService.get_rocks_by_user(user_id)
    
    # Get tasks for each rock
    tasks_by_rock = {}
    total_tasks = 0
    for rock in rocks:
        tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments)
        tasks_by_rock[str(rock.rock_id)] = {
            "rock": rock.model_dump(),
            "tasks": [task.model_dump() for task in tasks]
        }
        total_tasks += len(tasks)
    
    return {
        "user_id": str(user_id),
        "tasks_by_rock": tasks_by_rock,
        "total_tasks": total_tasks
    }

@router.put("/tasks/{task_id}/status", response_model=Task)
async def update_milestone_status(
    task_id: UUID,
    status_data: dict,
    current_user: User = Depends(get_current_user)
) -> Task:
    """Update milestone/task status (employees can update their assigned tasks)"""
    print(f"🔄 PUT /tasks/{task_id}/status called with data: {status_data}")
    
    # Get the task to verify it exists and get the rock
    task = await TaskService.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task/milestone not found"
        )
    
    # Get the rock to verify user access
    rock = await RockService.get_rock(task.rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated rock not found"
        )
    
    # Verify user has permission (facilitator or assigned employee)
    can_update = False
    
    # TEMPORARY: Allow facilitators for testing purposes
    # TODO: Remove this when testing is complete
    if current_user.employee_role == "facilitator":
        print("🧪 TESTING MODE: Allowing facilitator to update milestone status")
        can_update = True
    elif current_user.employee_role == "employee":
        # Check if task is for a rock assigned to this employee
        rock_dict = rock.model_dump()
        assigned_to_id = rock_dict.get('assigned_to_id')
        assigned_to_name = rock_dict.get('assigned_to', '').lower()
        current_user_name = current_user.employee_name.lower()
        
        if (assigned_to_id and str(assigned_to_id) == str(current_user.employee_id)) or \
           (assigned_to_name and assigned_to_name == current_user_name):
            can_update = True
    
    if not can_update:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update milestones for rocks assigned to you"
        )
    
    # Update the task status and completed fields
    new_status = status_data.get("status", "pending")
    new_completed = new_status in ["completed", "done"]
    
    print(f"🔄 Updating task status: {new_status}, completed: {new_completed}")
    
    # Create updated task data
    task_data = task.model_dump()
    task_data["status"] = new_status
    task_data["completed"] = new_completed
    task_data["updated_at"] = datetime.utcnow()
    
    # Create updated task object and save
    updated_task = Task(**task_data)
    result = await TaskService.update_task(task_id, updated_task)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task status"
        )
    
    print(f"✅ Task status updated successfully: {result.model_dump()}")
    return result 
