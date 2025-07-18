"""
Chatbot API Routes
Handles RAG-based conversations for rocks, issues, todos and general EOS questions
"""

from typing import List, Dict, Optional, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field

from service.chatbot_service import chatbot_service
from service.auth_service import get_current_user
from models.user import User

router = APIRouter()

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    timestamp: Optional[str] = None

class ChatRequest(BaseModel):
    question: str = Field(..., description="User's question or message")
    context_type: Optional[Literal["rock", "issue", "todo"]] = Field(None, description="Type of context for conversation")
    context_id: Optional[UUID] = Field(None, description="ID of the context item")
    conversation_history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation messages")

class PredefinedOptionsRequest(BaseModel):
    context_type: Optional[Literal["rock", "issue", "todo"]] = Field(None, description="Type of context")

class ChatResponse(BaseModel):
    response: str
    mode: str
    context_type: Optional[str] = None
    context_id: Optional[str] = None
    context_summary: Optional[Dict] = None
    predefined_options: List[str] = []
    timestamp: str
    error: bool = False

@router.post("/chat", response_model=ChatResponse)
async def chat_with_bot(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
) -> ChatResponse:
    """
    Main chatbot endpoint that handles both context-based and general conversations
    
    - **question**: The user's question or message
    - **context_type**: Optional type of context (rock, issue, todo)
    - **context_id**: Optional ID of the context item
    - **conversation_history**: Optional previous conversation messages
    """
    
    # Convert conversation history to the format expected by the service
    history = []
    if request.conversation_history:
        for msg in request.conversation_history:
            history.append({
                "role": msg.role,
                "content": msg.content
            })
    
    # Check authorization for context-based queries
    if request.context_type and request.context_id:
        # For non-facilitator users, we might want to check if they have access to the specific item
        # This is a simplified check - you can enhance based on your access control needs
        if current_user.employee_role != "facilitator":
            # Add access control logic here if needed
            # For now, we'll allow all authenticated users to access any context
            pass
    
    try:
        result = await chatbot_service.chat(
            user_question=request.question,
            context_type=request.context_type,
            context_id=request.context_id,
            conversation_history=history
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chatbot service error: {str(e)}"
        )

@router.get("/chat/options")
async def get_predefined_options(
    context_type: Optional[Literal["rock", "issue", "todo"]] = None,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Get predefined options for quick actions based on context type
    
    - **context_type**: Optional type of context (rock, issue, todo, or None for general)
    """
    
    options = chatbot_service.get_predefined_options(context_type)
    
    return {
        "context_type": context_type or "general",
        "options": options
    }

@router.post("/chat/quick-action", response_model=ChatResponse)
async def quick_action(
    action: str = Body(..., embed=True),
    context_type: Optional[Literal["rock", "issue", "todo"]] = Body(None, embed=True),
    context_id: Optional[UUID] = Body(None, embed=True),
    current_user: User = Depends(get_current_user)
) -> ChatResponse:
    """
    Execute a predefined quick action
    
    - **action**: The predefined action to execute
    - **context_type**: Type of context (rock, issue, todo)
    - **context_id**: ID of the context item
    """
    
    if not context_type or not context_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quick actions require both context_type and context_id"
        )
    
    # Check if the action is valid for the context type
    valid_options = chatbot_service.get_predefined_options(context_type)
    if action not in valid_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action '{action}' for context type '{context_type}'"
        )
    
    try:
        result = await chatbot_service.chat(
            user_question=action,
            context_type=context_type,
            context_id=context_id
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quick action failed: {str(e)}"
        )

@router.get("/chat/context/{context_type}/{context_id}/summary")
async def get_context_summary(
    context_type: Literal["rock", "issue", "todo"],
    context_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """
    Get a summary of the context item for chatbot initialization
    
    - **context_type**: Type of context (rock, issue, todo)
    - **context_id**: ID of the context item
    """
    
    try:
        context_data = await chatbot_service.get_context_data(context_type, context_id)
        
        if not context_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{context_type.title()} not found"
            )
        
        # Return a simplified summary for UI display
        summary = {
            "type": context_data["type"],
            "id": context_data["id"],
            "name": context_data.get("name") or context_data.get("title"),
            "status": context_data.get("status"),
            "assigned_to": context_data.get("assigned_to"),
            "predefined_options": chatbot_service.get_predefined_options(context_type)
        }
        
        # Add type-specific fields
        if context_type == "rock":
            summary.update({
                "smart_objective": context_data["smart_objective"],
                "total_tasks": context_data["total_tasks"]
            })
        elif context_type == "issue":
            summary.update({
                "description": context_data["description"][:200] + "..." if len(context_data["description"]) > 200 else context_data["description"],
                "raised_by": context_data["raised_by"],
                "linked_solution": context_data.get("linked_solution_ref")
            })
        elif context_type == "todo":
            summary.update({
                "due_date": context_data["due_date"],
                "designation": context_data["designation"],
                "linked_issue": context_data.get("linked_issue")
            })
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get context summary: {str(e)}"
        )
