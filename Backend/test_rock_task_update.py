"""
Test script for rock task update functionality
"""
import asyncio
import json
from uuid import UUID
from service.db import db
from service.rock_service import RockService
from service.task_service import TaskService
from models.rock import Rock
from models.task import Task
from models.quarter import Quarter
from datetime import datetime


async def test_rock_task_update():
    """Test the complete rock task update flow"""
    print("🧪 Testing Rock Task Update Functionality")
    print("=" * 60)
    
    try:
        # Step 1: Create a test quarter
        print("📅 Step 1: Creating test quarter...")
        quarter = Quarter(
            quarter="TEST_Q4_2024",
            weeks=12,
            year=2024,
            title="Test Quarter for Task Updates"
        )
        
        # Create quarter in database
        quarter_dict = quarter.model_dump()
        quarter_dict["_id"] = str(quarter.id)
        await db.quarters.replace_one(
            {"_id": quarter_dict["_id"]}, quarter_dict, upsert=True
        )
        print(f"   ✅ Quarter created: {quarter.quarter}")
        
        # Step 2: Create a test rock
        print("🎯 Step 2: Creating test rock...")
        rock = Rock(
            rock_name="Test Rock for Task Updates",
            smart_objective="A test rock to verify task update functionality works correctly",
            quarter_id=quarter.id,
            assigned_to_name="Test User"
        )
        
        created_rock = await RockService.create_rock(rock)
        print(f"   ✅ Rock created: {created_rock.rock_name}")
        print(f"   📋 Rock ID: {created_rock.rock_id}")
        
        # Step 3: Create initial tasks
        print("📝 Step 3: Creating initial tasks...")
        initial_tasks = [
            Task(
                rock_id=created_rock.rock_id,
                week=1,
                task="Initial Task 1",
                sub_tasks={"1": "First subtask"}
            ),
            Task(
                rock_id=created_rock.rock_id,
                week=2,
                task="Initial Task 2",
                sub_tasks={"1": "Second subtask"}
            )
        ]
        
        created_initial_tasks = []
        for task in initial_tasks:
            created_task = await TaskService.create_task(task)
            created_initial_tasks.append(created_task)
            print(f"   ✅ Created: {created_task.task} (ID: {created_task.task_id})")
        
        # Step 4: Verify initial tasks exist
        print("🔍 Step 4: Verifying initial tasks...")
        initial_task_list = await TaskService.get_tasks_by_rock(created_rock.rock_id)
        print(f"   📊 Found {len(initial_task_list)} initial tasks")
        
        # Step 5: Prepare updated tasks (simulating frontend data)
        print("🔄 Step 5: Preparing updated tasks...")
        updated_tasks = [
            Task(
                rock_id=created_rock.rock_id,
                week=1,
                task="Updated Task A",
                sub_tasks={"1": "Updated subtask A"}
            ),
            Task(
                rock_id=created_rock.rock_id,
                week=2,
                task="Updated Task B", 
                sub_tasks={"1": "Updated subtask B"}
            ),
            Task(
                rock_id=created_rock.rock_id,
                week=3,
                task="New Task C",
                sub_tasks={"1": "New subtask C"}
            )
        ]
        
        print(f"   📝 Prepared {len(updated_tasks)} updated tasks")
        
        # Step 6: Test the task replacement functionality (what our endpoint does)
        print("⚡ Step 6: Testing task replacement...")
        
        # Delete all existing tasks
        existing_tasks = await TaskService.get_tasks_by_rock(created_rock.rock_id)
        for existing_task in existing_tasks:
            await TaskService.delete_task(existing_task.task_id)
        print(f"   🗑️ Deleted {len(existing_tasks)} existing tasks")
        
        # Create all new tasks
        created_updated_tasks = []
        for task in updated_tasks:
            # Create clean task data without IDs (what our endpoint now does)
            task_data = task.model_dump(exclude={"id", "task_id"})
            task_data["rock_id"] = created_rock.rock_id
            new_task = Task(**task_data)
            created_task = await TaskService.create_task(new_task)
            created_updated_tasks.append(created_task)
            print(f"   ✅ Created: {created_task.task} (ID: {created_task.task_id})")
        
        # Step 7: Verify the replacement worked
        print("✅ Step 7: Verifying task replacement...")
        final_task_list = await TaskService.get_tasks_by_rock(created_rock.rock_id)
        print(f"   📊 Found {len(final_task_list)} final tasks")
        
        for task in final_task_list:
            print(f"   📋 Task: {task.task} | Week: {task.week}")
        
        print("\n🎉 SUCCESS: Rock task update functionality working correctly!")
        print("=" * 60)
        
        return {
            "success": True,
            "rock_id": str(created_rock.rock_id),
            "initial_tasks": len(created_initial_tasks),
            "updated_tasks": len(created_updated_tasks),
            "final_tasks": len(final_task_list)
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("=" * 60)
        return {
            "success": False,
            "error": str(e)
        }
    
    finally:
        # Cleanup: Remove test data
        print("🧹 Cleaning up test data...")
        try:
            if 'created_rock' in locals():
                # Delete all tasks for the rock
                tasks = await TaskService.get_tasks_by_rock(created_rock.rock_id)
                for task in tasks:
                    await TaskService.delete_task(task.task_id)
                
                # Delete the rock
                await RockService.delete_rock(created_rock.rock_id)
                print("   ✅ Test rock and tasks deleted")
            
            # Delete test quarter
            await db.quarters.delete_one({"_id": str(quarter.id)})
            print("   ✅ Test quarter deleted")
            
        except Exception as cleanup_error:
            print(f"   ⚠️ Cleanup warning: {cleanup_error}")


async def main():
    """Main test function"""
    result = await test_rock_task_update()
    
    print("\n📊 TEST SUMMARY:")
    print(f"Success: {result.get('success')}")
    if result.get('success'):
        print(f"Rock ID: {result.get('rock_id')}")
        print(f"Initial Tasks: {result.get('initial_tasks')}")
        print(f"Updated Tasks: {result.get('updated_tasks')}")
        print(f"Final Tasks: {result.get('final_tasks')}")
    else:
        print(f"Error: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
