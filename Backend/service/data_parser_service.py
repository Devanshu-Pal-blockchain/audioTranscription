"""
Data Parser Service - Parses pipeline final response into Rock and Task collections
"""

import json
import uuid
from typing import Dict, Any, List, Tuple
from datetime import datetime
import logging
import difflib
from .db import db
import asyncio

logger = logging.getLogger(__name__)

class DataParserService:
    def __init__(self):
        pass
    
    def parse_pipeline_response(self, pipeline_response: Dict[str, Any], quarter_id: str = "", participants: list = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse the pipeline final response into Rock and Task collections, generating unique UUIDs for each rock and task.
        Optionally inject quarter_id into each rock and map assigned_to_name to assigned_to_id using participants.
        
        Args:
            pipeline_response: The final response from the pipeline
            quarter_id: The quarter ID to inject into each rock (if provided)
            participants: List of participant dicts with name and id for mapping
            
        Returns:
            Tuple of (rocks_array, tasks_array) formatted according to schema, with UUIDs
        """
        try:
            rocks_array = []
            tasks_array = []
            name_to_id = {}
            name_list = []
            if participants:
                # Build a mapping from name to id (case-insensitive)
                name_to_id = {p["employee_name"].strip().lower(): p["employee_id"] for p in participants if p.get("employee_name") and p.get("employee_id")}
                name_list = [p["employee_name"].strip().lower() for p in participants if p.get("employee_name")]
            
            if "rocks" not in pipeline_response:
                logger.error("No 'rocks' field found in pipeline response")
                return [], []
            
            for rock in pipeline_response["rocks"]:
                # Generate UUID for this rock
                rock_uuid = str(uuid.uuid4())
                # Map assigned_to_name to assigned_to_id
                assigned_to_name = rock.get("owner", "")
                assigned_to_id = ""
                if assigned_to_name:
                    key = assigned_to_name.strip().lower()
                    # Try exact match first
                    assigned_to_id = name_to_id.get(key, "")
                    # If no exact match, use fuzzy matching
                    if not assigned_to_id and name_list:
                        close_matches = difflib.get_close_matches(key, name_list, n=1, cutoff=0.7)
                        if close_matches:
                            assigned_to_id = name_to_id.get(close_matches[0], "")
                # Parse Rock Collection
                rock_data = {
                    "rock_id": rock_uuid,  # Now filled with UUID
                    "rock_name": rock.get("rock_title", ""),
                    "smart_objective": rock.get("smart_objective", ""),
                    "quarter_id": quarter_id,  # Injected from argument
                    "assigned_to_id": assigned_to_id,  # Mapped from name
                    "assigned_to_name": assigned_to_name
                }
                rocks_array.append(rock_data)
                
                # Parse Task Collection for this rock
                if "weekly_tasks" in rock:
                    for week_data in rock["weekly_tasks"]:
                        week_number = week_data.get("week", 0)
                        
                        if "tasks" in week_data:
                            for task in week_data["tasks"]:
                                # Generate UUID for this task
                                task_uuid = str(uuid.uuid4())
                                task_data = {
                                    "rock_id": rock_uuid,  # Map to the parent rock's UUID
                                    "week": week_number,
                                    "task_id": task_uuid,  # Now filled with UUID
                                    "task": task.get("task_title", ""),
                                    "sub_tasks": task.get("sub_tasks", []),
                                    "comments": {
                                        "comment_id": "",
                                        "commented_by": ""
                                    }
                                }
                                tasks_array.append(task_data)
            
            logger.info(f"Successfully parsed {len(rocks_array)} rocks and {len(tasks_array)} tasks with UUIDs, quarter_id={quarter_id}, and assigned_to_id mapping")
            return rocks_array, tasks_array
            
        except Exception as e:
            logger.error(f"Error parsing pipeline response: {e}")
            return [], []
    
    async def insert_to_db(self, rocks_array, tasks_array):
        if rocks_array:
            await db.rocks.insert_many(rocks_array)
            # Ensure user assigned_rocks is in sync for each rock
            from service.user_service import UserService
            for rock in rocks_array:
                assigned_to_id = rock.get("assigned_to_id")
                rock_id = rock.get("rock_id")
                if assigned_to_id and rock_id:
                    try:
                        await UserService.assign_rock(UUID(assigned_to_id), UUID(rock_id))
                    except Exception as e:
                        logger.error(f"Failed to sync assigned_rocks for user {assigned_to_id} and rock {rock_id}: {e}")
        if tasks_array:
            await db.tasks.insert_many(tasks_array)
    
    async def save_parsed_data(self, rocks_array: List[Dict[str, Any]], tasks_array: List[Dict[str, Any]], file_prefix: str = None) -> Tuple[str, str]:
        """
        Save the parsed rocks and tasks arrays to separate JSON files and insert them into the database
        
        Args:
            rocks_array: Array of rock objects
            tasks_array: Array of task objects
            file_prefix: Optional prefix for file naming (ignored, kept for compatibility)
            
        Returns:
            Tuple of (rocks_file_path, tasks_file_path)
        """
        try:
            # Save rocks array
            rocks_file = "rocks.json"
            with open(rocks_file, "w", encoding="utf-8") as f:
                json.dump(rocks_array, f, indent=2, ensure_ascii=False)
            
            # Save tasks array
            tasks_file = "tasks.json"
            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(tasks_array, f, indent=2, ensure_ascii=False)
            
            # Insert into database directly from arrays
            try:
                await self.insert_to_db(rocks_array, tasks_array)
                logger.info(f"Inserted {len(rocks_array)} rocks and {len(tasks_array)} tasks into the database.")
            except Exception as db_exc:
                logger.error(f"Error inserting rocks/tasks into database: {db_exc}")
            
            logger.info(f"Parsed data saved to: {rocks_file} and {tasks_file}")
            return rocks_file, tasks_file
            
        except Exception as e:
            logger.error(f"Error saving parsed data: {e}")
            return "", ""
    
    async def parse_and_save(self, pipeline_response: Dict[str, Any], file_prefix: str = None, quarter_id: str = "", participants: list = None) -> Tuple[str, str]:
        """
        Parse pipeline response and save to files in one operation
        
        Args:
            pipeline_response: The final response from the pipeline
            file_prefix: Optional prefix for file naming
            quarter_id: The quarter ID to inject into each rock (if provided)
            participants: List of participant dicts with name and id for mapping
            
        Returns:
            Tuple of (rocks_file_path, tasks_file_path)
        """
        rocks_array, tasks_array = self.parse_pipeline_response(pipeline_response, quarter_id, participants)
        return await self.save_parsed_data(rocks_array, tasks_array, file_prefix)

# Convenience function for easy usage
async def parse_pipeline_response_to_files(pipeline_response: Dict[str, Any], file_prefix: str = None, quarter_id: str = "", participants: list = None) -> Tuple[str, str]:
    """
    Convenience function to parse pipeline response and save to files
    
    Args:
        pipeline_response: The final response from the pipeline
        file_prefix: Optional prefix for file naming
        quarter_id: The quarter ID to inject into each rock (if provided)
        participants: List of participant dicts with name and id for mapping
        
    Returns:
        Tuple of (rocks_file_path, tasks_file_path)
    """
    parser = DataParserService()
    return await parser.parse_and_save(pipeline_response, file_prefix, quarter_id, participants) 