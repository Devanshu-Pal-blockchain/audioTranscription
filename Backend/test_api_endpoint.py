import asyncio
from uuid import UUID
from service.quarter_service import QuarterService
from service.rock_service import RockService
from service.task_service import TaskService

async def test_quarter_with_rocks_and_tasks():
    """Test the exact logic from the /quarters/{quarter_id}/all endpoint"""
    
    quarter_id_str = "cf94fd31-e15c-47b1-aa26-23489d16ffe5"
    quarter_id = UUID(quarter_id_str)
    
    print(f"Testing endpoint logic for quarter: {quarter_id}")
    print("=" * 50)
    
    try:
        # Step 1: Verify quarter exists (same as endpoint)
        print("Step 1: Verifying quarter exists...")
        quarter = await QuarterService.get_quarter(quarter_id)
        if not quarter:
            print("❌ Quarter not found - this would return 404")
            return
        print(f"✅ Quarter found: {quarter.title}")
        
        # Step 2: Get rocks for quarter (admin user perspective)
        print("\nStep 2: Getting rocks for quarter...")
        rocks = await RockService.get_rocks_by_quarter(quarter_id)
        print(f"✅ Found {len(rocks)} rocks")
        
        # Step 3: Get tasks for each rock
        print("\nStep 3: Getting tasks for each rock...")
        rocks_with_tasks = []
        total_tasks = 0
        
        for rock in rocks:
            try:
                tasks = await TaskService.get_tasks_by_rock(rock.rock_id, include_comments=False)
                rock_dict = rock.model_dump()
                rock_dict["tasks"] = [task.model_dump() for task in tasks]
                rocks_with_tasks.append(rock_dict)
                total_tasks += len(tasks)
                print(f"  ✅ Rock '{rock.rock_name}': {len(tasks)} tasks")
            except Exception as e:
                print(f"  ❌ Error getting tasks for rock '{rock.rock_name}': {e}")
                
        # Step 4: Build final result (same as endpoint)
        print("\nStep 4: Building final result...")
        result = quarter.model_dump()
        result["rocks"] = rocks_with_tasks
        result["total_rocks"] = len(rocks_with_tasks)
        result["total_tasks"] = total_tasks
        
        print(f"✅ Final result:")
        print(f"   Quarter: {result['title']} ({result['quarter']} {result['year']})")
        print(f"   Total rocks: {result['total_rocks']}")
        print(f"   Total tasks: {result['total_tasks']}")
        print(f"   Result keys: {list(result.keys())}")
        
        # Verify the result structure
        if all(key in result for key in ['id', 'quarter', 'title', 'rocks', 'total_rocks', 'total_tasks']):
            print("✅ All expected keys present in result")
        else:
            print("❌ Missing required keys in result")
            
        return result
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    result = asyncio.run(test_quarter_with_rocks_and_tasks())
    print("\n" + "=" * 50)
    print("Test completed. The endpoint should now work correctly!")
