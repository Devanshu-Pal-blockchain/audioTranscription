#!/usr/bin/env python3
"""
Test script to verify the todo status update fix
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from service.todo_service import TodoService
from models.todo import Todo
from datetime import date, datetime
from uuid import uuid4

async def test_todo_update():
    print("🧪 Testing Todo Update Fix...")
    
    # Create a test todo
    test_todo = Todo(
        task_title="Test Todo for Update",
        assigned_to="Test User",
        designation="Tester",
        due_date=date.today(),
        status="pending",
        quarter_id=uuid4()
    )
    
    try:
        # Create the todo
        print("📝 Creating test todo...")
        created_todo = await TodoService.create_todo(test_todo)
        print(f"✅ Created todo with ID: {created_todo.todo_id}")
        print(f"📋 Original data: {created_todo.task_title} | {created_todo.assigned_to} | {created_todo.status}")
        
        # Update the status
        print("🔄 Updating todo status...")
        update_data = {"status": "completed"}
        updated_todo = await TodoService.update_todo(created_todo.todo_id, update_data)
        
        if updated_todo:
            print(f"✅ Updated successfully!")
            print(f"📋 Updated data: {updated_todo.task_title} | {updated_todo.assigned_to} | {updated_todo.status}")
            
            # Verify the data is preserved
            if (updated_todo.task_title == created_todo.task_title and 
                updated_todo.assigned_to == created_todo.assigned_to and 
                updated_todo.status == "completed"):
                print("🎉 SUCCESS: All data preserved correctly!")
            else:
                print("❌ FAILURE: Data was not preserved correctly!")
                print(f"Expected: {created_todo.task_title} | {created_todo.assigned_to} | completed")
                print(f"Got: {updated_todo.task_title} | {updated_todo.assigned_to} | {updated_todo.status}")
        else:
            print("❌ FAILURE: Update returned None!")
            
        # Clean up
        print("🧹 Cleaning up...")
        await TodoService.delete_todo(created_todo.todo_id)
        print("✅ Test completed!")
        
    except Exception as e:
        print(f"❌ ERROR during test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_todo_update())
