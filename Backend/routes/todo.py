from typing import List, Optional, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.todo import Todo
from service.todo_service import TodoService
from service.quarter_service import QuarterService
from service.auth_service import get_current_user, admin_required
from models.user import User
from datetime import datetime

router = APIRouter()

@router.post("/todos", response_model=Todo)
async def create_todo(
    todo: Todo,
    current_user: User = Depends(get_current_user)
) -> Todo:
    """Create a new todo"""
    # Verify quarter exists
    quarter = await QuarterService.get_quarter(todo.quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    
    created_todo = await TodoService.create_todo(todo)
    if not created_todo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create todo"
        )
    return created_todo

@router.get("/todos/{todo_id}", response_model=Todo)
async def get_todo(
    todo_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Todo:
    """Get a todo by ID"""
    todo = await TodoService.get_todo(todo_id)
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    # Check if user has access to this todo
    if (current_user.employee_role != "admin" and 
        todo.assigned_to_id and 
        str(todo.assigned_to_id) != str(current_user.employee_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this todo"
        )
    
    return todo

@router.get("/quarters/{quarter_id}/todos", response_model=List[Todo])
async def get_todos_by_quarter(
    quarter_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Todo]:
    """Get all todos for a specific quarter"""
    # Verify quarter exists
    quarter = await QuarterService.get_quarter(quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    
    todos = await TodoService.get_todos_by_quarter(quarter_id)
    
    # Filter todos based on user role
    if current_user.employee_role != "admin":
        todos = [todo for todo in todos 
                if todo.assigned_to_id is None or str(todo.assigned_to_id) == str(current_user.employee_id)]
    
    return todos

@router.get("/users/{user_id}/todos", response_model=List[Todo])
async def get_todos_by_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user)
) -> List[Todo]:
    """Get all todos assigned to a specific user"""
    # Check if user can access these todos
    if (current_user.employee_role != "admin" and 
        str(user_id) != str(current_user.employee_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own todos"
        )
    
    return await TodoService.get_todos_by_user(user_id)

@router.get("/todos", response_model=List[Todo])
async def get_todos_by_status(
    status: str,
    quarter_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user)
) -> List[Todo]:
    """Get todos by status, optionally filtered by quarter"""
    todos = await TodoService.get_todos_by_status(status, quarter_id)
    
    # Filter based on user role
    if current_user.employee_role != "admin":
        todos = [todo for todo in todos 
                if todo.assigned_to_id is None or str(todo.assigned_to_id) == str(current_user.employee_id)]
    
    return todos

@router.put("/todos/{todo_id}", response_model=Todo)
async def update_todo(
    todo_id: UUID,
    update_data: Dict,
    current_user: User = Depends(get_current_user)
) -> Todo:
    """Update a todo"""
    # Get existing todo
    existing_todo = await TodoService.get_todo(todo_id)
    if not existing_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    # Check permissions
    if (current_user.employee_role != "admin" and 
        existing_todo.assigned_to_id and 
        str(existing_todo.assigned_to_id) != str(current_user.employee_id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own todos"
        )
    
    updated_todo = await TodoService.update_todo(todo_id, update_data)
    if not updated_todo:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update todo"
        )
    
    return updated_todo

@router.delete("/todos/{todo_id}")
async def delete_todo(
    todo_id: UUID,
    current_user: User = Depends(admin_required)
) -> Dict[str, str]:
    """Delete a todo (admin only)"""
    success = await TodoService.delete_todo(todo_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    return {"message": "Todo deleted successfully"}

@router.get("/todos/overdue", response_model=List[Todo])
async def get_overdue_todos(
    current_user: User = Depends(get_current_user)
) -> List[Todo]:
    """Get all overdue todos"""
    todos = await TodoService.get_overdue_todos()
    
    # Filter based on user role
    if current_user.employee_role != "admin":
        todos = [todo for todo in todos 
                if todo.assigned_to_id is None or str(todo.assigned_to_id) == str(current_user.employee_id)]
    
    return todos

@router.get("/todos/due-soon", response_model=List[Todo])
async def get_todos_due_soon(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user)
) -> List[Todo]:
    """Get todos due within specified days"""
    todos = await TodoService.get_todos_due_soon(days)
    
    # Filter based on user role
    if current_user.employee_role != "admin":
        todos = [todo for todo in todos 
                if todo.assigned_to_id is None or str(todo.assigned_to_id) == str(current_user.employee_id)]
    
    return todos

@router.get("/todos/statistics", response_model=Dict)
async def get_todo_statistics(
    quarter_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get statistics about todos"""
    if current_user.employee_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view todo statistics"
        )
    
    return await TodoService.get_todo_statistics(quarter_id)
