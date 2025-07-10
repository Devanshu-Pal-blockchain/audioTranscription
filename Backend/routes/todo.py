from typing import List, Dict, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Query
from datetime import datetime, timedelta

from models.todo import ToDo, ToDoCreate, ToDoUpdate
from models.user import User
from service.todo_service import ToDoService
from service.auth_service import get_current_user, facilitator_required

router = APIRouter()

@router.post("/todos", response_model=ToDo)
async def create_todo(
    todo: ToDoCreate,
    current_user: User = Depends(facilitator_required)
) -> ToDo:
    """Create a new todo (facilitator only)"""
    todo_data = todo.model_dump()
    todo_data["todo_id"] = uuid4()
    
    # Validate timeframe (1-14 days)
    if not await ToDoService.validate_timeframe(todo_data["deadline"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Todo deadline must be within 1-14 days from now"
        )
    
    return await ToDoService.create_todo(todo_data)

@router.get("/todos/{todo_id}", response_model=ToDo)
async def get_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user)
) -> ToDo:
    """Get a todo by ID"""
    todo = await ToDoService.get_todo(todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    # Check access - users can only view their own todos unless they're facilitator
    if current_user.employee_role != "facilitator" and str(todo.owner_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this todo"
        )
    
    return todo

@router.get("/todos", response_model=List[ToDo])
async def list_todos(
    meeting_id: Optional[UUID] = Query(None),
    owner_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    parent_rock_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user)
) -> List[ToDo]:
    """List todos with optional filters"""
    
    if meeting_id:
        todos = await ToDoService.get_todos_by_meeting(meeting_id)
    elif owner_id:
        # Users can only view their own todos unless they're facilitator
        if current_user.employee_role != "facilitator" and owner_id != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only view your own todos"
            )
        todos = await ToDoService.get_todos_by_owner(owner_id)
    elif status:
        todos = await ToDoService.get_todos_by_status(status)
    elif parent_rock_id:
        todos = await ToDoService.get_todos_by_parent_rock(parent_rock_id)
    else:
        # For non-facilitators, only show their own todos
        if current_user.employee_role != "facilitator":
            todos = await ToDoService.get_todos_by_owner(current_user.employee_id)
        else:
            todos = await ToDoService.get_all_todos()
    
    return todos

@router.get("/todos/user/{user_id}", response_model=List[ToDo])
async def list_user_todos(
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[ToDo]:
    """List all todos assigned to a specific user"""
    # Users can only view their own todos unless they're facilitator
    if current_user.employee_role != "facilitator" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own todos"
        )
    return await ToDoService.get_todos_by_owner(user_id)

@router.get("/todos/overdue", response_model=List[ToDo])
async def list_overdue_todos(
    current_user: User = Depends(get_current_user)
) -> List[ToDo]:
    """List all overdue todos"""
    todos = await ToDoService.get_overdue_todos()
    
    # Filter by user if not facilitator
    if current_user.employee_role != "facilitator":
        todos = [todo for todo in todos if str(todo.owner_id) == str(current_user.employee_id)]
    
    return todos

@router.get("/todos/due-soon", response_model=List[ToDo])
async def list_due_soon_todos(
    days: int = Query(3, ge=1, le=14),
    current_user: User = Depends(get_current_user)
) -> List[ToDo]:
    """List todos due within specified days"""
    todos = await ToDoService.get_due_soon_todos(days)
    
    # Filter by user if not facilitator
    if current_user.employee_role != "facilitator":
        todos = [todo for todo in todos if str(todo.owner_id) == str(current_user.employee_id)]
    
    return todos

@router.put("/todos/{todo_id}", response_model=ToDo)
async def update_todo(
    todo_id: UUID,
    todo_update: ToDoUpdate,
    current_user: User = Depends(get_current_user)
) -> ToDo:
    """Update a todo"""
    # Get current todo to check ownership
    current_todo = await ToDoService.get_todo(todo_id)
    if not current_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    # Check access - users can only edit their own todos unless they're facilitator
    if current_user.employee_role != "facilitator" and str(current_todo.owner_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this todo"
        )
    
    update_data = todo_update.model_dump(exclude_unset=True)
    
    # Validate timeframe if deadline is being updated
    if "deadline" in update_data:
        if not await ToDoService.validate_timeframe(update_data["deadline"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Todo deadline must be within 1-14 days from now"
            )
    
    todo = await ToDoService.update_todo(todo_id, update_data)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    return todo

@router.patch("/todos/{todo_id}/status")
async def update_todo_status(
    todo_id: UUID,
    status: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Update todo status"""
    # Validate status
    valid_statuses = ["pending", "in_progress", "completed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Get current todo to check ownership
    current_todo = await ToDoService.get_todo(todo_id)
    if not current_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    # Check access - users can only edit their own todos unless they're facilitator
    if current_user.employee_role != "facilitator" and str(current_todo.owner_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this todo"
        )
    
    todo = await ToDoService.update_todo_status(todo_id, status)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    return {"message": f"Todo status updated to {status}"}

@router.post("/todos/{todo_id}/complete")
async def mark_todo_completed(
    todo_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Mark todo as completed"""
    # Get current todo to check ownership
    current_todo = await ToDoService.get_todo(todo_id)
    if not current_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    # Check access - users can only edit their own todos unless they're facilitator
    if current_user.employee_role != "facilitator" and str(current_todo.owner_id) != str(current_user.employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this todo"
        )
    
    todo = await ToDoService.mark_todo_completed(todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    return {"message": "Todo marked as completed"}

@router.delete("/todos/{todo_id}")
async def delete_todo(
    todo_id: UUID,
    current_user: User = Depends(facilitator_required)
) -> dict:
    """Delete a todo (facilitator only)"""
    success = await ToDoService.delete_todo(todo_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    return {"message": "Todo deleted successfully"}

@router.get("/todos/search/{search_term}", response_model=List[ToDo])
async def search_todos(
    search_term: str,
    current_user: User = Depends(get_current_user)
) -> List[ToDo]:
    """Search todos by title or description"""
    todos = await ToDoService.search_todos(search_term)
    
    # Filter by user if not facilitator
    if current_user.employee_role != "facilitator":
        todos = [todo for todo in todos if str(todo.owner_id) == str(current_user.employee_id)]
    
    return todos

@router.get("/todos/statistics", response_model=Dict)
async def get_todo_statistics(
    current_user: User = Depends(facilitator_required)
) -> Dict:
    """Get todo statistics (facilitator only)"""
    return await ToDoService.get_todo_statistics()

@router.get("/todos/user/{user_id}/completion-rate", response_model=Dict)
async def get_user_completion_rate(
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get completion rate for a specific user"""
    # Users can only view their own stats unless they're facilitator
    if current_user.employee_role != "facilitator" and current_user.employee_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own completion rate"
        )
    
    return await ToDoService.get_completion_rate_by_owner(user_id)

@router.post("/todos/bulk", response_model=List[ToDo])
async def bulk_create_todos(
    todos_data: List[ToDoCreate],
    current_user: User = Depends(facilitator_required)
) -> List[ToDo]:
    """Bulk create multiple todos (facilitator only)"""
    # Validate timeframes for all todos
    for todo_data in todos_data:
        if not await ToDoService.validate_timeframe(todo_data.deadline):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Todo '{todo_data.title}' deadline must be within 1-14 days from now"
            )
    
    # Convert to dict format with UUIDs
    todos_dict = []
    for todo in todos_data:
        todo_dict = todo.model_dump()
        todo_dict["todo_id"] = uuid4()
        todos_dict.append(todo_dict)
    
    return await ToDoService.bulk_create_todos(todos_dict)

@router.patch("/todos/bulk/status")
async def bulk_update_todo_status(
    todo_ids: List[UUID],
    status: str,
    current_user: User = Depends(facilitator_required)
) -> Dict[str, int]:
    """Bulk update status for multiple todos (facilitator only)"""
    # Validate status
    valid_statuses = ["pending", "in_progress", "completed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    modified_count = await ToDoService.bulk_update_status(todo_ids, status)
    return {"modified_count": modified_count}
