import asyncio
from uuid import UUID
from service.quarter_service import QuarterService
from service.rock_service import RockService
from service.task_service import TaskService

async def debug_quarter_lookup():
    """Debug quarter lookup issues"""
    
    # Test the quarter ID from your data
    quarter_id_str = "cf94fd31-e15c-47b1-aa26-23489d16ffe5"
    quarter_id_uuid = UUID(quarter_id_str)
    
    print(f"Testing quarter ID: {quarter_id_str}")
    print(f"As UUID: {quarter_id_uuid}")
    print("---")
    
    # Test 1: Check if quarter exists with different query methods
    print("Test 1: Direct database query")
    from service.db import db
    quarter_dict = await db.quarters.find_one({"id": quarter_id_str})
    print(f"Direct query result: {quarter_dict is not None}")
    if quarter_dict:
        print(f"Quarter title: {quarter_dict.get('title')}")
    
    quarter_dict_uuid = await db.quarters.find_one({"id": quarter_id_uuid})
    print(f"UUID query result: {quarter_dict_uuid is not None}")
    print("---")
    
    # Test 2: Check QuarterService.get_quarter
    print("Test 2: QuarterService.get_quarter")
    quarter = await QuarterService.get_quarter(quarter_id_uuid)
    print(f"QuarterService result: {quarter is not None}")
    if quarter:
        print(f"Quarter title: {quarter.title}")
    print("---")
    
    # Test 3: Check rocks for this quarter
    print("Test 3: RockService.get_rocks_by_quarter")
    rocks = await RockService.get_rocks_by_quarter(quarter_id_uuid)
    print(f"Number of rocks found: {len(rocks)}")
    for rock in rocks:
        print(f"Rock: {rock.rock_name} (ID: {rock.rock_id})")
    print("---")
    
    # Test 4: Check tasks for each rock
    print("Test 4: TaskService.get_tasks_by_rock")
    for rock in rocks:
        try:
            tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments=False)
            print(f"Rock {rock.rock_name}: {len(tasks)} tasks")
        except Exception as e:
            print(f"Error getting tasks for rock {rock.rock_name}: {e}")

if __name__ == "__main__":
    asyncio.run(debug_quarter_lookup())
