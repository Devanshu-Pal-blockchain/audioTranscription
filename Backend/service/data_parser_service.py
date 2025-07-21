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
from utils.secure_fields import encrypt_dict

logger = logging.getLogger(__name__)

class DataParserService:
    def __init__(self):
        pass
    
    def validate_and_map_participant(self, name: str, participants: Optional[List] = None) -> Tuple[Optional[str], str]:
        """
        Enhanced participant validation with Chain of Thought reasoning for better accuracy.
        
        Args:
            name: The name to validate and map
            participants: List of participant dictionaries
            
        Returns:
            Tuple of (employee_id or None, validated_name)
        """
        if not name or not name.strip():
            logger.warning("Empty or None name provided for participant mapping")
            return None, ""
            
        # Clean up the input name
        cleaned_name = name.strip()
        
        # Handle "UNASSIGNED" prefix cases
        if cleaned_name.startswith("UNASSIGNED:"):
            original_name = cleaned_name.replace("UNASSIGNED:", "").strip()
            logger.info(f"Processing UNASSIGNED case: '{original_name}'")
            # Try to match the original name after removing UNASSIGNED prefix
            if original_name and participants:
                result_id, result_name = self._attempt_participant_matching(original_name, participants)
                if result_id:
                    logger.info(f"Successfully mapped previously UNASSIGNED '{original_name}' to '{result_name}' (ID: {result_id})")
                    return result_id, result_name
            # If still no match, return as unassigned
            return None, f"UNASSIGNED: {original_name}" if original_name else "UNASSIGNED"
            
        if not participants:
            logger.warning(f"No participants list provided - cannot map name '{cleaned_name}' to ID")
            return None, cleaned_name
            
        return self._attempt_participant_matching(cleaned_name, participants)
    
    def _attempt_participant_matching(self, name: str, participants: List) -> Tuple[Optional[str], str]:
        """
        Systematic participant matching using Chain of Thought approach.
        """
        name_key = name.lower().strip()
        
        # Build comprehensive participant mapping
        participant_mappings = []
        for p in participants:
            employee_name = p.get("employee_name", "").strip()
            employee_id = p.get("employee_id")
            
            if employee_name and employee_id:
                participant_mappings.append({
                    "name": employee_name,
                    "name_lower": employee_name.lower(),
                    "id": str(employee_id),
                    "name_parts": employee_name.lower().split(),
                    "first_name": employee_name.split()[0].lower() if employee_name.split() else "",
                    "last_name": employee_name.split()[-1].lower() if len(employee_name.split()) > 1 else ""
                })
        
        logger.info(f"Attempting to match '{name}' against {len(participant_mappings)} participants")
        
        # Strategy 1: Exact match (case-insensitive)
        for p in participant_mappings:
            if name_key == p["name_lower"]:
                logger.info(f"✅ Exact match: '{name}' -> '{p['name']}' (ID: {p['id']})")
                return p["id"], p["name"]
        
        # Strategy 2: Exact match ignoring common prefixes/suffixes
        cleaned_name_key = self._clean_name_for_matching(name_key)
        for p in participant_mappings:
            cleaned_participant = self._clean_name_for_matching(p["name_lower"])
            if cleaned_name_key == cleaned_participant:
                logger.info(f"✅ Clean match: '{name}' -> '{p['name']}' (ID: {p['id']})")
                return p["id"], p["name"]
        
        # Strategy 3: Fuzzy matching with higher threshold
        participant_names = [p["name_lower"] for p in participant_mappings]
        close_matches = difflib.get_close_matches(name_key, participant_names, n=1, cutoff=0.85)
        if close_matches:
            matched_name_lower = close_matches[0]
            matched_participant = next(p for p in participant_mappings if p["name_lower"] == matched_name_lower)
            logger.info(f"✅ Fuzzy match: '{name}' -> '{matched_participant['name']}' (ID: {matched_participant['id']})")
            return matched_participant["id"], matched_participant["name"]
        
        # Strategy 4: First + Last name combination matching
        input_parts = name_key.split()
        if len(input_parts) >= 2:
            input_first = input_parts[0]
            input_last = input_parts[-1]
            
            for p in participant_mappings:
                if (input_first == p["first_name"] and input_last == p["last_name"]):
                    logger.info(f"✅ First+Last match: '{name}' -> '{p['name']}' (ID: {p['id']})")
                    return p["id"], p["name"]
        
        # Strategy 5: Partial name matching (any significant part)
        for p in participant_mappings:
            for input_part in input_parts:
                if len(input_part) > 3:  # Only consider meaningful parts
                    for name_part in p["name_parts"]:
                        if input_part == name_part:
                            logger.info(f"✅ Partial match: '{name}' -> '{p['name']}' (ID: {p['id']}) [matched on '{input_part}']")
                            return p["id"], p["name"]
        
        # Strategy 6: Common name variations and nicknames
        name_variations = self._get_name_variations(name_key)
        for variation in name_variations:
            for p in participant_mappings:
                if variation == p["name_lower"] or variation in p["name_parts"]:
                    logger.info(f"✅ Variation match: '{name}' (as '{variation}') -> '{p['name']}' (ID: {p['id']})")
                    return p["id"], p["name"]
        
        # No match found
        available_names = [p["name"] for p in participant_mappings]
        logger.warning(f"❌ No match found for '{name}' in participants: {available_names}")
        return None, name
    
    def _clean_name_for_matching(self, name: str) -> str:
        """Remove common prefixes, suffixes, and titles for better matching"""
        # Remove common titles and prefixes
        prefixes_to_remove = ["mr.", "mrs.", "ms.", "dr.", "prof.", "sir", "madam"]
        suffixes_to_remove = ["jr.", "sr.", "ii", "iii", "esq."]
        
        cleaned = name.lower().strip()
        
        # Remove prefixes
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix + " "):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove suffixes
        for suffix in suffixes_to_remove:
            if cleaned.endswith(" " + suffix):
                cleaned = cleaned[:-len(suffix)].strip()
        
        return cleaned
    
    def _get_name_variations(self, name: str) -> List[str]:
        """Generate common name variations and nicknames"""
        variations = []
        name_lower = name.lower().strip()
        
        # Common nickname mappings
        nickname_map = {
            "william": ["bill", "will", "billy"],
            "robert": ["bob", "rob", "bobby"],
            "richard": ["rick", "dick", "richie"],
            "michael": ["mike", "micky"],
            "christopher": ["chris", "topher"],
            "matthew": ["matt"],
            "andrew": ["andy", "drew"],
            "anthony": ["tony"],
            "jonathan": ["jon", "johnny"],
            "benjamin": ["ben", "benny"],
            "alexander": ["alex", "al"],
            "nicholas": ["nick", "nicky"],
            "elizabeth": ["liz", "beth", "betty"],
            "jennifer": ["jen", "jenny"],
            "jessica": ["jess", "jessie"],
            "michelle": ["mich", "mickey"],
            "stephanie": ["steph", "steffi"],
            "katherine": ["kate", "kathy", "katie"],
            "patricia": ["pat", "patty", "trish"],
            "margaret": ["meg", "maggie", "peggy"]
        }
        
        # Add direct variations
        for full_name, nicknames in nickname_map.items():
            if full_name in name_lower:
                variations.extend(nicknames)
            if name_lower in nicknames:
                variations.append(full_name)
        
        # Add initials-based variations
        parts = name_lower.split()
        if len(parts) >= 2:
            # First initial + last name
            variations.append(f"{parts[0][0]}. {parts[-1]}")
            # First name + last initial
            variations.append(f"{parts[0]} {parts[-1][0]}.")
        
        return variations
    
    def assign_rock_with_validation(self, rock_data: Dict[str, Any], owner_name: str, participants: Optional[List] = None) -> Dict[str, Any]:
        """
        Enhanced rock assignment with Chain of Thought validation and better accuracy.
        """
        if not owner_name or not owner_name.strip():
            logger.info("Rock has no owner specified - creating unassigned rock")
            rock_data["assigned_to_id"] = None
            rock_data["assigned_to_name"] = ""
            return rock_data
        
        # Clean up owner name
        cleaned_owner_name = owner_name.strip()
        
        # Use enhanced validation method
        owner_id, validated_name = self.validate_and_map_participant(cleaned_owner_name, participants)
        
        if owner_id:
            # Valid participant found
            rock_data["assigned_to_id"] = owner_id
            rock_data["assigned_to_name"] = validated_name
            logger.info(f"✅ Rock '{rock_data.get('rock_name', 'Unknown')}' successfully assigned to {validated_name} (ID: {owner_id})")
        else:
            # Enhanced unassignment handling
            if cleaned_owner_name.startswith("UNASSIGNED"):
                # Already marked as unassigned by LLM
                rock_data["assigned_to_id"] = None
                rock_data["assigned_to_name"] = cleaned_owner_name
                logger.info(f"ℹ️ Rock '{rock_data.get('rock_name', 'Unknown')}' is intentionally unassigned: {cleaned_owner_name}")
            else:
                # No valid participant found - create descriptive unassigned entry
                logger.warning(f"⚠️ Rock '{rock_data.get('rock_name', 'Unknown')}' cannot be assigned to '{cleaned_owner_name}' - no matching participant found")
                rock_data["assigned_to_id"] = None
                rock_data["assigned_to_name"] = f"UNASSIGNED: {cleaned_owner_name}"
        
        return rock_data
    
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

            if "rocks" not in pipeline_response:
                logger.error("No 'rocks' field found in pipeline response")
                return [], [], [], [], []

            for rock in pipeline_response["rocks"]:
                rock_uuid = str(uuid.uuid4())
                # Support both old format (rock_owner) and new format (owner)
                owner_name = rock.get("rock_owner", "") or rock.get("owner", "")
                
                # Support both old format (smart_rock) and new format (rock_title + smart_objective)
                rock_name = rock.get("smart_rock", "") or rock.get("rock_title", "")
                smart_objective = rock.get("smart_rock", "") or rock.get("smart_objective", "")
                
                # Clean up rock name if it has a colon separator
                if ":" in rock_name:
                    rock_name = rock_name.split(":")[0]
                
                rock_data = {
                    "id": rock_uuid,
                    "rock_id": rock_uuid,
                    "rock_name": rock_name,
                    "smart_objective": smart_objective,
                    "quarter_id": quarter_id,
                    "created_at": dt.datetime.utcnow().isoformat(),
                    "updated_at": dt.datetime.utcnow().isoformat()
                }
                
                # Use validation method to assign rock properly
                rock_data = self.assign_rock_with_validation(rock_data, owner_name, participants)
                rocks_array.append(rock_data)
                
                # Parse Task Collection for this rock - support both 'milestones' and 'weekly_tasks' structures
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
                
                # Handle 'weekly_tasks' structure (new OpenAI format)
                elif "weekly_tasks" in rock:
                    for week_data in rock["weekly_tasks"]:
                        week_number = week_data.get("week", 0)
                        tasks = week_data.get("tasks", [])
                        for task in tasks:
                            task_uuid = str(uuid.uuid4())
                            task_title = task.get("task_title", "")
                            sub_tasks = task.get("sub_tasks", [])
                            
                            task_data = {
                                "id": task_uuid,
                                "rock_id": rock_uuid,
                                "week": week_number,
                                "task_id": task_uuid,
                                "task": task_title,
                                "sub_tasks": sub_tasks if sub_tasks else None,
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
                    
                    # Use validation method to map name to ID
                    assigned_to_id, validated_name = self.validate_and_map_participant(assigned_to_name, participants)
                    
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
                        "assigned_to": validated_name if assigned_to_id else f"UNASSIGNED: {assigned_to_name}" if assigned_to_name else "",
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
                    
                    # Use validation method to map name to ID
                    raised_by_id, validated_name = self.validate_and_map_participant(raised_by_name, participants)
                    
                    issue_data = {
                        "id": issue_uuid,
                        "issue_id": issue_uuid,
                        "issue_title": issue.get("issue_title", ""),
                        "description": issue.get("description", ""),
                        "raised_by": validated_name if raised_by_id else f"UNASSIGNED: {raised_by_name}" if raised_by_name else "",
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
    
    async def insert_to_db(self, rocks_array, milestones_array, todos_array, issues_array, runtime_solutions_array, session_summary=None, quarter_id=None):
        """Insert parsed data into database collections and update quarter with session summary"""
        try:
            # Define fields to exclude from encryption
            exclude_fields = ["id", "rock_id", "task_id", "todo_id", "issue_id", "assigned_to_id", "assigned_to_name", "raised_by_id", "raised_by", "created_at", "updated_at", "quarter_id", "status"]
            
            # Save session summary to quarter if provided
            if session_summary and quarter_id:
                await self._save_session_summary_to_quarter(quarter_id, session_summary)
            
            # Insert rocks
            if rocks_array:
                encrypted_rocks = [encrypt_dict(dict(rock), exclude_fields) for rock in rocks_array]
                await db.rocks.insert_many(encrypted_rocks)
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
                encrypted_tasks = [encrypt_dict(dict(task), exclude_fields) for task in milestones_array]
                await db.tasks.insert_many(encrypted_tasks)
                logger.info(f"Inserted {len(milestones_array)} tasks into database")
            # Insert todos
            if todos_array:
                encrypted_todos = [encrypt_dict(dict(todo), exclude_fields) for todo in todos_array]
                await db.todos.insert_many(encrypted_todos)
                logger.info(f"Inserted {len(todos_array)} todos into database")
            # Insert issues
            if issues_array:
                encrypted_issues = [encrypt_dict(dict(issue), exclude_fields) for issue in issues_array]
                await db.issues.insert_many(encrypted_issues)
                logger.info(f"Inserted {len(issues_array)} issues into database")
            # Note: runtime_solutions are not stored in database for now
            if runtime_solutions_array:
                logger.info(f"Runtime solutions saved to file only: {len(runtime_solutions_array)} items")
        except Exception as e:
            logger.error(f"Error inserting data into database: {e}")
            raise

    async def _save_session_summary_to_quarter(self, quarter_id: str, session_summary: dict):
        """Extract and save session summary to quarter"""
        try:
            from service.quarter_service import QuarterService
            from uuid import UUID
            
            # Extract session summary text from the structured summary
            summary_text = ""
            if isinstance(session_summary, dict):
                # Create a comprehensive summary text from all sections
                sections = []
                if "meeting_overview" in session_summary:
                    sections.append(f"Meeting Overview: {session_summary['meeting_overview']}")
                if "strategic_themes" in session_summary:
                    sections.append(f"Strategic Themes: {session_summary['strategic_themes']}")
                if "participant_roles" in session_summary:
                    sections.append(f"Participant Roles: {session_summary['participant_roles']}")
                if "issues_landscape" in session_summary:
                    sections.append(f"Issues Landscape: {session_summary['issues_landscape']}")
                if "task_allocation" in session_summary:
                    sections.append(f"Task Allocation: {session_summary['task_allocation']}")
                if "strategic_direction" in session_summary:
                    sections.append(f"Strategic Direction: {session_summary['strategic_direction']}")
                if "implementation_timeline" in session_summary:
                    sections.append(f"Implementation Timeline: {session_summary['implementation_timeline']}")
                
                summary_text = " ".join(sections)
            elif isinstance(session_summary, str):
                summary_text = session_summary
            
            if summary_text and quarter_id:
                quarter_uuid = UUID(quarter_id)
                updated_quarter = await QuarterService.update_session_summary(quarter_uuid, summary_text)
                if updated_quarter:
                    logger.info(f"Successfully updated session summary for quarter {quarter_id}")
                else:
                    logger.warning(f"Failed to update session summary for quarter {quarter_id}")
        except Exception as e:
            logger.error(f"Error saving session summary to quarter {quarter_id}: {e}")
    
    async def save_parsed_data(self, rocks_array: List[Dict[str, Any]], milestones_array: List[Dict[str, Any]], todos_array: List[Dict[str, Any]], issues_array: List[Dict[str, Any]], runtime_solutions_array: List[Dict[str, Any]], file_prefix: Optional[str] = None, session_summary=None, quarter_id=None) -> Tuple[str, str, str, str, str]:
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
                await self.insert_to_db(rocks_array, milestones_array, todos_array, issues_array, runtime_solutions_array, session_summary, quarter_id)
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
        session_summary = pipeline_response.get("session_summary")
        return await self.save_parsed_data(rocks_array, milestones_array, todos_array, issues_array, runtime_solutions_array, file_prefix, session_summary, quarter_id)

# Convenience function for easy usage
async def parse_pipeline_response_to_files(pipeline_response: Dict[str, Any], file_prefix: Optional[str] = None, quarter_id: str = "", participants: Optional[List] = None) -> Tuple[str, str, str, str, str]:
    parser = DataParserService()
    return await parser.parse_and_save(pipeline_response, file_prefix, quarter_id, participants)