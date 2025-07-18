from typing import List, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from models.rock import Rock, RockPayload
from models.task import Task
from service.rock_service import RockService
from service.task_service import TaskService
from service.auth_service import get_current_user, facilitator_required
from models.user import User
from service.edit_milestones_service import process_custom_rock_payload

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
    if current_user.employee_role != "facilitator" and str(rock.assigned_to_id) != str(current_user.employee_id):
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
    current_user: User = Depends(facilitator_required)
) -> Dict:
    """Create new tasks for a rock (facilitator only)"""
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
    current_user: User = Depends(facilitator_required)
) -> Dict:
    """Replace all tasks for a rock with new tasks (facilitator only)"""
    print(f"🔄 PUT /rocks/{rock_id}/tasks called")
    print(f"📝 Received {len(tasks)} tasks")
    
    rock = await RockService.get_rock(rock_id)
    if not rock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rock not found"
        )
    
    # Step 1: Delete all existing tasks for this rock
    existing_tasks = await TaskService.get_tasks_by_rock(rock_id)
    print(f"🗑️ Deleting {len(existing_tasks)} existing tasks")
    for existing_task in existing_tasks:
        await TaskService.delete_task(existing_task.task_id)
    
    # Step 2: Create all new tasks
    created_tasks = []
    for i, task in enumerate(tasks):
        try:
            print(f"📝 Processing task {i+1}: {task.model_dump()}")
            
            # Create clean task data without IDs
            task_data = task.model_dump(exclude={"id", "task_id"})
            task_data["rock_id"] = rock_id
            
            # Handle problematic fields that cause validation errors
            if task_data.get("sub_tasks") is None:
                task_data["sub_tasks"] = {}
                print(f"   🔧 Fixed null sub_tasks to empty dict")
                
            if task_data.get("comments") is None:
                task_data["comments"] = []
                print(f"   🔧 Fixed null comments to empty list")
            
            # Ensure week is positive integer
            if "week" not in task_data or task_data["week"] <= 0:
                task_data["week"] = 1
                print(f"   🔧 Fixed week to 1")
            
            # Ensure task name is not empty
            if not task_data.get("task") or task_data["task"].strip() == "":
                task_data["task"] = "Default task"
                print(f"   🔧 Fixed empty task name")
            
            print(f"   ✅ Clean task data: {task_data}")
            
            new_task = Task(**task_data)
            created_task = await TaskService.create_task(new_task)
            created_tasks.append(created_task)
            print(f"   ✅ Created task: {created_task.task} (ID: {created_task.task_id})")
            
        except Exception as e:
            print(f"❌ ERROR creating task {i+1}: {e}")
            print(f"📋 Failed task data: {task.model_dump()}")
            print(f"📋 Processed task data: {task_data}")
            
            # Return specific error details
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": f"Failed to create task {i+1}",
                    "message": str(e),
                    "task_data": task.model_dump(),
                    "field_issues": {
                        "sub_tasks": task_data.get("sub_tasks"),
                        "comments": task_data.get("comments"),
                        "week": task_data.get("week"),
                        "task": task_data.get("task")
                    }
                }
            )
    
    print(f"✅ Successfully created {len(created_tasks)} tasks")
    
    result = rock.model_dump()
    result["tasks"] = [task.model_dump() for task in created_tasks]
    return result

@router.delete("/rocks/{rock_id}/tasks")
async def delete_rock_tasks(
    rock_id: UUID,
    current_user: User = Depends(facilitator_required)
) -> dict:
    """Delete all tasks for a rock (facilitator only)"""
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
    if current_user.employee_role == "facilitator":
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
    current_user: User = Depends(facilitator_required)
) -> Rock:
    """Update a rock's SMART objective (facilitator only)"""
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
    current_user: User = Depends(facilitator_required)
) -> Dict:
    """Bulk create rocks and their tasks (facilitator only)"""
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

@router.post("/rocks/payload", response_model=dict)
async def accept_rock_payload(payload: RockPayload = Body(...)):
    """Accept a rock payload from the frontend, generate the LLM prompt, and return it (no DB interaction)."""
    result = process_custom_rock_payload(payload)
    return result 
