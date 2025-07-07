"""
Data Parser Service - Parses pipeline final response into Rock and Task collections
"""

import json
import uuid
from typing import Dict, Any, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataParserService:
    def __init__(self):
        pass
    
    def parse_pipeline_response(self, pipeline_response: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse the pipeline final response into Rock and Task collections, generating unique UUIDs for each rock and task.
        
        Args:
            pipeline_response: The final response from the pipeline
            
        Returns:
            Tuple of (rocks_array, tasks_array) formatted according to schema, with UUIDs
        """
        try:
            rocks_array = []
            tasks_array = []
            
            if "rocks" not in pipeline_response:
                logger.error("No 'rocks' field found in pipeline response")
                return [], []
            
            for rock in pipeline_response["rocks"]:
                # Generate UUID for this rock
                rock_uuid = str(uuid.uuid4())
                # Parse Rock Collection
                rock_data = {
                    "rock_id": rock_uuid,  # Now filled with UUID
                    "rock_name": rock.get("rock_title", ""),
                    "smart_objective": rock.get("smart_objective", ""),
                    "quarter_id": "",  # Empty as specified
                    "assigned_to_id": "",  # Empty as specified
                    "assigned_to_name": rock.get("owner", "")
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
            
            logger.info(f"Successfully parsed {len(rocks_array)} rocks and {len(tasks_array)} tasks with UUIDs")
            return rocks_array, tasks_array
            
        except Exception as e:
            logger.error(f"Error parsing pipeline response: {e}")
            return [], []
    
    def save_parsed_data(self, rocks_array: List[Dict[str, Any]], tasks_array: List[Dict[str, Any]], file_prefix: str = None) -> Tuple[str, str]:
        """
        Save the parsed rocks and tasks arrays to separate JSON files
        
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
            
            logger.info(f"Parsed data saved to: {rocks_file} and {tasks_file}")
            return rocks_file, tasks_file
            
        except Exception as e:
            logger.error(f"Error saving parsed data: {e}")
            return "", ""
    
    def parse_and_save(self, pipeline_response: Dict[str, Any], file_prefix: str = None) -> Tuple[str, str]:
        """
        Parse pipeline response and save to files in one operation
        
        Args:
            pipeline_response: The final response from the pipeline
            file_prefix: Optional prefix for file naming
            
        Returns:
            Tuple of (rocks_file_path, tasks_file_path)
        """
        rocks_array, tasks_array = self.parse_pipeline_response(pipeline_response)
        return self.save_parsed_data(rocks_array, tasks_array, file_prefix)

# Convenience function for easy usage
def parse_pipeline_response_to_files(pipeline_response: Dict[str, Any], file_prefix: str = None) -> Tuple[str, str]:
    """
    Convenience function to parse pipeline response and save to files
    
    Args:
        pipeline_response: The final response from the pipeline
        file_prefix: Optional prefix for file naming
        
    Returns:
        Tuple of (rocks_file_path, tasks_file_path)
    """
    parser = DataParserService()
    return parser.parse_and_save(pipeline_response, file_prefix) 