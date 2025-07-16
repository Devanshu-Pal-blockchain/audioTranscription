"""
RAG-based Chatbot Service for Rocks, Issues, and Todos
Supports both context-based and general conversations
"""

import os
import json
from typing import Dict, List, Optional, Any, Literal
from uuid import UUID
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

from models.rock import Rock
from models.issue import Issue
from models.todo import Todo
from models.task import Task
from service.rock_service import RockService
from service.issue_service import IssueService
from service.todo_service import TodoService
from service.task_service import TaskService

load_dotenv()

class ChatbotService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.default_model = "gpt-3.5-turbo"
        
        # Predefined options for quick actions
        self.predefined_options = {
            "rock": [
                "Explain this rock's objective",
                "Summarize key milestones",
                "Show task breakdown",
                "Analyze progress status",
                "Suggest improvements",
                "Show timeline overview"
            ],
            "issue": [
                "Explain this issue",
                "Summarize the problem",
                "Show linked solutions",
                "Analyze impact",
                "Suggest resolution steps",
                "Show discussion notes"
            ],
            "todo": [
                "Explain this todo",
                "Show task details",
                "Check deadline status",
                "Show assigned person",
                "Analyze priority",
                "Show related issues"
            ],
            "general": [
                "What is EOS?",
                "Explain rocks and goals",
                "How do issues work?",
                "Tell me about todos",
                "What are milestones?",
                "How to track progress?"
            ]
        }

    async def get_context_data(
        self, 
        context_type: Literal["rock", "issue", "todo"], 
        context_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Retrieve detailed context data for the specified item"""
        try:
            if context_type == "rock":
                rock = await RockService.get_rock(context_id)
                if not rock:
                    return None
                    
                # Get all tasks for this rock
                tasks = await TaskService.get_tasks_by_rock(context_id)
                
                return {
                    "type": "rock",
                    "id": str(rock.rock_id),
                    "name": rock.rock_name,
                    "smart_objective": rock.smart_objective,
                    "assigned_to": rock.assigned_to_name,
                    "assigned_to_id": str(rock.assigned_to_id) if rock.assigned_to_id else None,
                    "quarter_id": str(rock.quarter_id),
                    "created_at": rock.created_at.isoformat(),
                    "updated_at": rock.updated_at.isoformat(),
                    "tasks": [
                        {
                            "task_id": str(task.task_id),
                            "task": task.task,
                            "week": task.week,
                            "sub_tasks": task.sub_tasks,
                            "comments": task.comments,
                            "created_at": task.created_at.isoformat(),
                            "updated_at": task.updated_at.isoformat()
                        } for task in tasks
                    ],
                    "total_tasks": len(tasks)
                }
                
            elif context_type == "issue":
                issue = await IssueService.get_issue(context_id)
                if not issue:
                    return None
                    
                return {
                    "type": "issue",
                    "id": str(issue.issue_id),
                    "title": issue.issue_title,
                    "description": issue.description,
                    "raised_by": issue.raised_by,
                    "raised_by_id": str(issue.raised_by_id) if issue.raised_by_id else None,
                    "discussion_notes": issue.discussion_notes,
                    "linked_solution_type": issue.linked_solution_type,
                    "linked_solution_ref": issue.linked_solution_ref,
                    "status": issue.status,
                    "quarter_id": str(issue.quarter_id),
                    "created_at": issue.created_at.isoformat(),
                    "updated_at": issue.updated_at.isoformat()
                }
                
            elif context_type == "todo":
                todo = await TodoService.get_todo(context_id)
                if not todo:
                    return None
                    
                return {
                    "type": "todo",
                    "id": str(todo.todo_id),
                    "title": todo.task_title,
                    "assigned_to": todo.assigned_to,
                    "assigned_to_id": str(todo.assigned_to_id) if todo.assigned_to_id else None,
                    "designation": todo.designation,
                    "due_date": todo.due_date.isoformat(),
                    "linked_issue": todo.linked_issue,
                    "status": todo.status,
                    "quarter_id": str(todo.quarter_id),
                    "created_at": todo.created_at.isoformat(),
                    "updated_at": todo.updated_at.isoformat()
                }
                
        except Exception as e:
            print(f"Error retrieving context data: {e}")
            return None
        
        return None

    def create_context_prompt(
        self,
        context_data: Dict[str, Any],
        user_question: str
    ) -> str:
        """Create a concise, specific, bullet-pointed prompt with context data"""
        context_type = context_data["type"]

        if context_type == "rock":
            return f"""
You are an expert EOS (Entrepreneurial Operating System) consultant. Answer the user's question about the following Rock (quarterly goal) in clear, specific bullet points only. Be brief and to the point.

ROCK CONTEXT:
- Name: {context_data['name']}
- SMART Objective: {context_data['smart_objective']}
- Assigned To: {context_data['assigned_to']} (ID: {context_data['assigned_to_id']})
- Quarter: {context_data['quarter_id']}
- Created: {context_data['created_at']}
- Last Updated: {context_data['updated_at']}
- Total Tasks: {context_data['total_tasks']}

TASKS:
{self._format_tasks_for_prompt(context_data['tasks'])}

USER QUESTION: {user_question}

Respond ONLY in concise, relevant bullet points. Avoid lengthy explanations. Focus on actionable, clear, and direct answers.
"""

        elif context_type == "issue":
            return f"""
You are an expert EOS (Entrepreneurial Operating System) consultant. Answer the user's question about the following Issue in clear, specific bullet points only. Be brief and to the point.

ISSUE CONTEXT:
- Title: {context_data['title']}
- Description: {context_data['description']}
- Raised By: {context_data['raised_by']} (ID: {context_data['raised_by_id']})
- Status: {context_data['status']}
- Quarter: {context_data['quarter_id']}
- Created: {context_data['created_at']}
- Last Updated: {context_data['updated_at']}
- Linked Solution Type: {context_data['linked_solution_type'] or 'Not linked'}
- Linked Solution Reference: {context_data['linked_solution_ref'] or 'None'}
- Discussion Notes: {context_data['discussion_notes'] or 'No discussion notes available'}

USER QUESTION: {user_question}

Respond ONLY in concise, relevant bullet points. Avoid lengthy explanations. Focus on actionable, clear, and direct answers.
"""

        elif context_type == "todo":
            return f"""
You are an expert EOS (Entrepreneurial Operating System) consultant. Answer the user's question about the following Todo in clear, specific bullet points only. Be brief and to the point.

TODO CONTEXT:
- Task Title: {context_data['title']}
- Assigned To: {context_data['assigned_to']} ({context_data['designation']})
- Assigned To ID: {context_data['assigned_to_id']}
- Due Date: {context_data['due_date']}
- Status: {context_data['status']}
- Quarter: {context_data['quarter_id']}
- Created: {context_data['created_at']}
- Last Updated: {context_data['updated_at']}
- Linked Issue: {context_data['linked_issue'] or 'No linked issue'}
- Deadline Analysis: {self._analyze_deadline(context_data['due_date'], context_data['status'])}

USER QUESTION: {user_question}

Respond ONLY in concise, relevant bullet points. Avoid lengthy explanations. Focus on actionable, clear, and direct answers.
"""

        # Default fallback (should not reach here)
        return f"Unable to create context prompt for type: {context_type}"

    def _format_tasks_for_prompt(self, tasks: List[Dict]) -> str:
        """Format tasks for inclusion in prompt"""
        if not tasks:
            return "No tasks defined for this rock."
        
        formatted = []
        for i, task in enumerate(tasks, 1):
            # Handle None values safely
            sub_tasks = task.get('sub_tasks') or {}
            comments = task.get('comments') or []
            
            formatted.append(f"""
Task {i}: {task['task']}
- Week: {task['week']}
- Sub-tasks: {len(sub_tasks)} items
- Comments: {len(comments)} comments
- Created: {task.get('created_at', 'Unknown')}
""")
        return "\n".join(formatted)

    def _analyze_deadline(self, due_date_str: str, status: str) -> str:
        """Analyze deadline status"""
        try:
            from datetime import date
            due_date = datetime.fromisoformat(due_date_str).date()
            today = date.today()
            days_diff = (due_date - today).days
            
            if status == "completed":
                return "✅ Task completed"
            elif days_diff < 0:
                return f"⚠️ OVERDUE by {abs(days_diff)} days"
            elif days_diff == 0:
                return "🔥 DUE TODAY"
            elif days_diff <= 3:
                return f"⚡ Due in {days_diff} days (URGENT)"
            elif days_diff <= 7:
                return f"📅 Due in {days_diff} days"
            else:
                return f"📅 Due in {days_diff} days"
        except:
            return "📅 Due date analysis unavailable"

    def create_general_prompt(self, user_question: str) -> str:
        """Create concise, bullet-pointed prompt for general EOS questions"""
        return f"""
You are an expert EOS (Entrepreneurial Operating System) consultant. Answer the user's question about EOS in clear, specific bullet points only. Be brief and to the point.

USER QUESTION: {user_question}

Respond ONLY in concise, relevant bullet points. Avoid lengthy explanations. Focus on actionable, clear, and direct answers.
"""

    async def chat(
        self,
        user_question: str,
        context_type: Optional[Literal["rock", "issue", "todo"]] = None,
        context_id: Optional[UUID] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Main chat method that handles both context-based and general conversations
        """
        try:
            # Prepare context data if in context mode
            context_data = None
            if context_type and context_id:
                context_data = await self.get_context_data(context_type, context_id)
                if not context_data:
                    return {
                        "response": f"Sorry, I couldn't find the {context_type} with the specified ID.",
                        "context_type": context_type,
                        "context_id": str(context_id) if context_id else None,
                        "predefined_options": self.predefined_options.get(context_type, [])
                    }

            # Create the appropriate prompt
            if context_data:
                system_prompt = self.create_context_prompt(context_data, user_question)
                mode = "context"
            else:
                system_prompt = self.create_general_prompt(user_question)
                mode = "general"

            # Prepare conversation messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history[-10:])  # Last 10 messages for context
            
            # Add current user question
            messages.append({"role": "user", "content": user_question})

            # Get response from OpenAI
            response = self.openai_client.chat.completions.create(
                model=self.default_model,
                messages=messages,  # type: ignore
                max_tokens=1000,
                temperature=0.7
            )

            bot_response = response.choices[0].message.content

            # Prepare response with metadata
            result = {
                "response": bot_response,
                "mode": mode,
                "context_type": context_type,
                "context_id": str(context_id) if context_id else None,
                "predefined_options": self.predefined_options.get(context_type or "general", []),
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add context summary if in context mode
            if context_data:
                result["context_summary"] = {
                    "type": context_data["type"],
                    "id": context_data["id"],
                    "name": context_data.get("name") or context_data.get("title"),
                    "status": context_data.get("status"),
                    "total_tasks": context_data.get("total_tasks") if context_data["type"] == "rock" else None
                }

            return result

        except Exception as e:
            return {
                "response": f"I apologize, but I encountered an error while processing your question: {str(e)}",
                "error": True,
                "context_type": context_type,
                "context_id": str(context_id) if context_id else None,
                "predefined_options": self.predefined_options.get(context_type or "general", [])
            }

    def get_predefined_options(
        self, 
        context_type: Optional[Literal["rock", "issue", "todo"]] = None
    ) -> List[str]:
        """Get predefined options for quick actions"""
        return self.predefined_options.get(context_type or "general", [])

# Singleton instance
chatbot_service = ChatbotService()
