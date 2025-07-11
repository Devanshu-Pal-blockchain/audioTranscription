"""
Data Parser Service - Parses pipeline final response into Rock and Task collections
"""

import json
import uuid
from typing import Dict, Any, List, Tuple, Optional
import datetime as dt
import logging
import difflib
from .db import db
import asyncio
import re
import os

logger = logging.getLogger(__name__)

class DataParserService:
    def __init__(self):
        pass
    
    def parse_pipeline_response(self, pipeline_response: Dict[str, Any], quarter_id: str = "", participants: Optional[List] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse the pipeline final response into Rock, Task, Todo, Issue, and Runtime Solution collections, generating unique UUIDs for each.
        Optionally inject quarter_id into each rock and map assigned_to_name to assigned_to_id using participants.
        Returns:
            Tuple of (rocks_array, tasks_array, todos_array, issues_array, runtime_solutions_array)
        """
        try:
            rocks_array = []
            milestones_array = []
            todos_array = []
            issues_array = []
            runtime_solutions_array = []
            name_to_id = {}
            name_list = []
            if participants:
                name_to_id = {p["employee_name"].strip().lower(): p["employee_id"] for p in participants if p.get("employee_name") and p.get("employee_id")}
                name_list = [p["employee_name"].strip().lower() for p in participants if p.get("employee_name")]

            if "rocks" not in pipeline_response:
                logger.error("No 'rocks' field found in pipeline response")
                return [], [], [], [], []

            for rock in pipeline_response["rocks"]:
                rock_uuid = str(uuid.uuid4())
                owner_name = rock.get("rock_owner", "")
                owner_id = ""
                if owner_name:
                    key = owner_name.strip().lower()
                    owner_id = name_to_id.get(key, "")
                    if not owner_id and name_list:
                        close_matches = difflib.get_close_matches(key, name_list, n=1, cutoff=0.7)
                        if close_matches:
                            owner_id = name_to_id.get(close_matches[0], "")
                rock_data = {
                    "id": rock_uuid,
                    "rock_id": rock_uuid,
                    "rock_name": rock.get("smart_rock", "").split(":")[0] if ":" in rock.get("smart_rock", "") else rock.get("smart_rock", ""),
                    "smart_objective": rock.get("smart_rock", ""),
                    "quarter_id": quarter_id,
                    "assigned_to_id": owner_id,
                    "assigned_to_name": owner_name,
                    "created_at": dt.datetime.utcnow().isoformat(),
                    "updated_at": dt.datetime.utcnow().isoformat()
                }
                rocks_array.append(rock_data)
                # Parse Task Collection for this rock using 'milestones'
                if "milestones" in rock:
                    for milestone in rock["milestones"]:
                        week_number = milestone.get("week", 0)
                        # Handle 'milestones' (list of strings)
                        if "milestones" in milestone and isinstance(milestone["milestones"], list):
                            for ms in milestone["milestones"]:
                                task_uuid = str(uuid.uuid4())
                                task_data = {
                                    "id": task_uuid,
                                    "rock_id": rock_uuid,
                                    "week": week_number,
                                    "task_id": task_uuid,
                                    "task": ms if isinstance(ms, str) else str(ms),
                                    "sub_tasks": None,
                                    "comments": [],
                                    "created_at": dt.datetime.utcnow().isoformat(),
                                    "updated_at": dt.datetime.utcnow().isoformat()
                                }
                                milestones_array.append(task_data)
                        # Handle 'milestone' (single string)
                        elif "milestone" in milestone and isinstance(milestone["milestone"], str):
                            task_uuid = str(uuid.uuid4())
                            task_data = {
                                "id": task_uuid,
                                "rock_id": rock_uuid,
                                "week": week_number,
                                "task_id": task_uuid,
                                "task": milestone["milestone"],
                                "sub_tasks": None,
                                "comments": [],
                                "created_at": dt.datetime.utcnow().isoformat(),
                                "updated_at": dt.datetime.utcnow().isoformat()
                            }
                            milestones_array.append(task_data)
            
            # Parse todos
            if "todos" in pipeline_response:
                for todo in pipeline_response["todos"]:
                    todo_uuid = str(uuid.uuid4())
                    assigned_to_name = todo.get("assigned_to", "")
                    assigned_to_id = None
                    
                    # Find matching participant
                    if assigned_to_name and participants:
                        for participant in participants:
                            if participant.get("employee_name", "").strip().lower() == assigned_to_name.strip().lower():
                                assigned_to_id = str(participant.get("employee_id", ""))
                                break
                    
                    # Parse due_date
                    due_date = todo.get("due_date", "")
                    if due_date:
                        try:
                            from datetime import datetime
                            if isinstance(due_date, str):
                                # Try to parse the date string
                                parsed_date = datetime.strptime(due_date, "%Y-%m-%d").date()
                                due_date = parsed_date.isoformat()
                        except ValueError:
                            # If parsing fails, keep the original string
                            pass
                    
                    todo_data = {
                        "id": todo_uuid,
                        "todo_id": todo_uuid,
                        "task_title": todo.get("task_title", ""),
                        "assigned_to": assigned_to_name,
                        "designation": todo.get("designation", ""),
                        "due_date": due_date,
                        "linked_issue": todo.get("linked_issue"),
                        "status": "pending",
                        "quarter_id": quarter_id,
                        "assigned_to_id": assigned_to_id,
                        "created_at": dt.datetime.utcnow().isoformat(),
                        "updated_at": dt.datetime.utcnow().isoformat()
                    }
                    todos_array.append(todo_data)
            
            # Parse issues
            if "issues" in pipeline_response:
                for issue in pipeline_response["issues"]:
                    issue_uuid = str(uuid.uuid4())
                    raised_by_name = issue.get("raised_by", "")
                    raised_by_id = None
                    
                    # Find matching participant
                    if raised_by_name and participants:
                        for participant in participants:
                            if participant.get("employee_name", "").strip().lower() == raised_by_name.strip().lower():
                                raised_by_id = str(participant.get("employee_id", ""))
                                break
                    
                    issue_data = {
                        "id": issue_uuid,
                        "issue_id": issue_uuid,
                        "issue_title": issue.get("issue_title", ""),
                        "description": issue.get("description", ""),
                        "raised_by": raised_by_name,
                        "discussion_notes": issue.get("discussion_notes"),
                        "linked_solution_type": issue.get("linked_solution_type"),
                        "linked_solution_ref": issue.get("linked_solution_ref"),
                        "status": "open",
                        "quarter_id": quarter_id,
                        "raised_by_id": raised_by_id,
                        "created_at": dt.datetime.utcnow().isoformat(),
                        "updated_at": dt.datetime.utcnow().isoformat()
                    }
                    issues_array.append(issue_data)
            
            # Parse runtime_solutions
            if "runtime_solutions" in pipeline_response:
                for rs in pipeline_response["runtime_solutions"]:
                    runtime_solutions_array.append(rs)
            logger.info(f"Successfully parsed {len(rocks_array)} rocks, {len(milestones_array)} milestones, {len(todos_array)} todos, {len(issues_array)} issues, {len(runtime_solutions_array)} runtime solutions with UUIDs, quarter_id={quarter_id}, and owner_id mapping")
            return rocks_array, milestones_array, todos_array, issues_array, runtime_solutions_array
        except Exception as e:
            logger.error(f"Error parsing pipeline response: {e}")
            return [], [], [], [], []
    
    async def insert_to_db(self, rocks_array, milestones_array, todos_array, issues_array, runtime_solutions_array):
        """Insert parsed data into database collections"""
        try:
            # Insert rocks
            if rocks_array:
                await db.rocks.insert_many(rocks_array)
                logger.info(f"Inserted {len(rocks_array)} rocks into database")
                
                # Ensure user assigned_rocks is in sync for each rock
                from service.user_service import UserService
                from uuid import UUID
                for rock in rocks_array:
                    assigned_to_id = rock.get("assigned_to_id")
                    rock_id = rock.get("rock_id")
                    if assigned_to_id and rock_id:
                        try:
                            await UserService.assign_rock(UUID(str(assigned_to_id)), UUID(str(rock_id)))
                        except Exception as e:
                            logger.error(f"Failed to sync assigned_rocks for user {assigned_to_id} and rock {rock_id}: {e}")
            
            # Insert milestones (tasks)
            if milestones_array:
                await db.tasks.insert_many(milestones_array)
                logger.info(f"Inserted {len(milestones_array)} tasks into database")
            
            # Insert todos
            if todos_array:
                await db.todos.insert_many(todos_array)
                logger.info(f"Inserted {len(todos_array)} todos into database")
            
            # Insert issues
            if issues_array:
                await db.issues.insert_many(issues_array)
                logger.info(f"Inserted {len(issues_array)} issues into database")
            
            # Note: runtime_solutions are not stored in database for now
            if runtime_solutions_array:
                logger.info(f"Runtime solutions saved to file only: {len(runtime_solutions_array)} items")
                
        except Exception as e:
            logger.error(f"Error inserting data into database: {e}")
            raise
    
    async def save_parsed_data(self, rocks_array: List[Dict[str, Any]], milestones_array: List[Dict[str, Any]], todos_array: List[Dict[str, Any]], issues_array: List[Dict[str, Any]], runtime_solutions_array: List[Dict[str, Any]], file_prefix: Optional[str] = None) -> Tuple[str, str, str, str, str]:
        """
        Save the parsed arrays to separate JSON files and insert them into the database (rocks/tasks only for now)
        Returns:
            Tuple of (rocks_file_path, tasks_file_path, todos_file_path, issues_file_path, runtime_solutions_file_path)
        """
        try:
            output_dir = "output"
            os.makedirs(output_dir, exist_ok=True)
            rocks_file = os.path.join(output_dir, "rocks.json")
            with open(rocks_file, "w", encoding="utf-8") as f:
                json.dump(rocks_array, f, indent=2, ensure_ascii=False)
            milestones_file = os.path.join(output_dir, "milestones.json")
            with open(milestones_file, "w", encoding="utf-8") as f:
                json.dump(milestones_array, f, indent=2, ensure_ascii=False)
            todos_file = os.path.join(output_dir, "todos.json")
            with open(todos_file, "w", encoding="utf-8") as f:
                json.dump(todos_array, f, indent=2, ensure_ascii=False)
            issues_file = os.path.join(output_dir, "issues.json")
            with open(issues_file, "w", encoding="utf-8") as f:
                json.dump(issues_array, f, indent=2, ensure_ascii=False)
            runtime_solutions_file = os.path.join(output_dir, "runtime_solutions.json")
            with open(runtime_solutions_file, "w", encoding="utf-8") as f:
                json.dump(runtime_solutions_array, f, indent=2, ensure_ascii=False)
            # Insert into database
            try:
                await self.insert_to_db(rocks_array, milestones_array, todos_array, issues_array, runtime_solutions_array)
                logger.info(f"Successfully inserted all data into database")
            except Exception as db_exc:
                logger.error(f"Error inserting data into database: {db_exc}")
            logger.info(f"Parsed data saved to: {rocks_file}, {milestones_file}, {todos_file}, {issues_file}, {runtime_solutions_file}")
            return rocks_file, milestones_file, todos_file, issues_file, runtime_solutions_file
        except Exception as e:
            logger.error(f"Error saving parsed data: {e}")
            return "", "", "", "", ""

    async def parse_and_save(self, pipeline_response: Dict[str, Any], file_prefix: Optional[str] = None, quarter_id: str = "", participants: Optional[List] = None) -> Tuple[str, str, str, str, str]:
        rocks_array, milestones_array, todos_array, issues_array, runtime_solutions_array = self.parse_pipeline_response(pipeline_response, quarter_id, participants)
        return await self.save_parsed_data(rocks_array, milestones_array, todos_array, issues_array, runtime_solutions_array, file_prefix)

# Convenience function for easy usage
async def parse_pipeline_response_to_files(pipeline_response: Dict[str, Any], file_prefix: Optional[str] = None, quarter_id: str = "", participants: Optional[List] = None) -> Tuple[str, str, str, str, str]:
    parser = DataParserService()
    return await parser.parse_and_save(pipeline_response, file_prefix, quarter_id, participants) 