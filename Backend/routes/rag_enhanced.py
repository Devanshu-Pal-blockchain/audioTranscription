from typing import List, Dict, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from models.user import User
from service.rag_vector_service import RagVectorService
from service.meeting_service import MeetingService
from service.ids_analysis_service import IDSAnalysisService
from service.auth_service import get_current_user, admin_required

router = APIRouter()

@router.post("/rag/query", response_model=Dict)
async def query_rag_system(
    query: str = Body(..., embed=True),
    context_filters: Optional[Dict] = Body(None, embed=True),
    limit: int = Body(10, embed=True, ge=1, le=50),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Query the RAG system with context-aware filtering"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await RagVectorService.query_with_context(
        query=query,
        context_filters=context_filters,
        limit=limit,
        user_filter=user_filter
    )

@router.post("/rag/meeting-query", response_model=Dict)
async def query_meeting_context(
    meeting_id: UUID,
    query: str = Body(..., embed=True),
    include_related: bool = Body(True, embed=True),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Query specific meeting context with related IDS items"""
    # Check meeting access
    meeting = await MeetingService.get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found"
        )
    
    if (current_user.employee_role != "admin" and 
        current_user.employee_id not in meeting.attendees and
        current_user.employee_id != meeting.created_by):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this meeting"
        )
    
    return await RagVectorService.query_meeting_context(
        meeting_id=meeting_id,
        query=query,
        include_related=include_related
    )

@router.post("/rag/ids-analysis", response_model=Dict)
async def analyze_transcript_for_ids(
    meeting_id: UUID,
    analysis_type: str = Body(..., embed=True),
    current_user: User = Depends(admin_required)
) -> Dict:
    """Analyze meeting transcript for Issues, Decisions, Solutions using RAG"""
    valid_types = ["issues", "decisions", "solutions", "all"]
    if analysis_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid analysis type. Must be one of: {', '.join(valid_types)}"
        )
    
    return await IDSAnalysisService.analyze_meeting_transcript(
        meeting_id=meeting_id,
        analysis_type=analysis_type
    )

@router.post("/rag/semantic-search", response_model=Dict)
async def semantic_search(
    query: str = Body(..., embed=True),
    search_scope: str = Body("all", embed=True),
    date_from: Optional[str] = Body(None, embed=True),
    date_to: Optional[str] = Body(None, embed=True),
    limit: int = Body(20, embed=True, ge=1, le=100),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Perform semantic search across all VTO content"""
    valid_scopes = ["all", "meetings", "rocks", "issues", "solutions", "milestones"]
    if search_scope not in valid_scopes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search scope. Must be one of: {', '.join(valid_scopes)}"
        )
    
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await RagVectorService.semantic_search(
        query=query,
        search_scope=search_scope,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        user_filter=user_filter
    )

@router.get("/rag/similar-content/{content_id}", response_model=List[Dict])
async def find_similar_content(
    content_id: UUID,
    content_type: str = Query(..., description="Type of content (meeting, rock, issue, solution, milestone)"),
    limit: int = Query(10, ge=1, le=50, description="Number of similar items to return"),
    current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """Find content similar to a specific item"""
    valid_types = ["meeting", "rock", "issue", "solution", "milestone"]
    if content_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type. Must be one of: {', '.join(valid_types)}"
        )
    
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await RagVectorService.find_similar_content(
        content_id=content_id,
        content_type=content_type,
        limit=limit,
        user_filter=user_filter
    )

@router.post("/rag/generate-insights", response_model=Dict)
async def generate_insights(
    quarter_id: Optional[UUID] = Body(None, embed=True),
    focus_areas: List[str] = Body([], embed=True),
    insight_type: str = Body("summary", embed=True),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Generate AI-powered insights from VTO data"""
    valid_insight_types = ["summary", "trends", "recommendations", "risks", "opportunities"]
    if insight_type not in valid_insight_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid insight type. Must be one of: {', '.join(valid_insight_types)}"
        )
    
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await RagVectorService.generate_insights(
        quarter_id=quarter_id,
        focus_areas=focus_areas,
        insight_type=insight_type,
        user_filter=user_filter
    )

@router.post("/rag/index-meeting", response_model=Dict)
async def index_meeting_content(
    meeting_id: UUID,
    reindex: bool = Body(False, embed=True),
    current_user: User = Depends(admin_required)
) -> Dict:
    """Index or reindex meeting content for RAG (admin only)"""
    success = await RagVectorService.index_meeting_content(
        meeting_id=meeting_id,
        reindex=reindex
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meeting not found or indexing failed"
        )
    
    return {"message": "Meeting content indexed successfully", "meeting_id": str(meeting_id)}

@router.post("/rag/bulk-index", response_model=Dict)
async def bulk_index_content(
    content_types: List[str] = Body(..., embed=True),
    quarter_id: Optional[UUID] = Body(None, embed=True),
    force_reindex: bool = Body(False, embed=True),
    current_user: User = Depends(admin_required)
) -> Dict:
    """Bulk index content for RAG system (admin only)"""
    valid_types = ["meetings", "rocks", "issues", "solutions", "milestones"]
    invalid_types = [t for t in content_types if t not in valid_types]
    if invalid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content types: {', '.join(invalid_types)}. Valid types: {', '.join(valid_types)}"
        )
    
    results = await RagVectorService.bulk_index_content(
        content_types=content_types,
        quarter_id=quarter_id,
        force_reindex=force_reindex
    )
    
    return results

@router.get("/rag/search-suggestions", response_model=List[str])
async def get_search_suggestions(
    partial_query: str = Query(..., min_length=2, description="Partial search query"),
    limit: int = Query(10, ge=1, le=20, description="Number of suggestions to return"),
    current_user: User = Depends(get_current_user)
) -> List[str]:
    """Get search suggestions based on partial query"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await RagVectorService.get_search_suggestions(
        partial_query=partial_query,
        limit=limit,
        user_filter=user_filter
    )

@router.post("/rag/ask-ai", response_model=Dict)
async def ask_ai_about_content(
    question: str = Body(..., embed=True),
    context_ids: List[UUID] = Body([], embed=True),
    context_type: Optional[str] = Body(None, embed=True),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Ask AI questions about specific content with context"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await RagVectorService.ask_ai_with_context(
        question=question,
        context_ids=context_ids,
        context_type=context_type,
        user_filter=user_filter
    )

@router.get("/rag/content-graph/{content_id}", response_model=Dict)
async def get_content_relationship_graph(
    content_id: UUID,
    content_type: str = Query(..., description="Type of content"),
    depth: int = Query(2, ge=1, le=5, description="Relationship depth"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get relationship graph for content item"""
    return await RagVectorService.get_content_relationship_graph(
        content_id=content_id,
        content_type=content_type,
        depth=depth,
        user_id=current_user.employee_id if current_user.employee_role != "admin" else None
    )

@router.post("/rag/extract-entities", response_model=Dict)
async def extract_entities_from_text(
    text: str = Body(..., embed=True),
    entity_types: List[str] = Body(["PERSON", "ORG", "DATE", "WORK_OF_ART"], embed=True),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Extract named entities from text"""
    return await RagVectorService.extract_entities(
        text=text,
        entity_types=entity_types
    )

@router.get("/rag/trending-topics", response_model=List[Dict])
async def get_trending_topics(
    time_range_days: int = Query(30, ge=7, le=365, description="Time range in days"),
    limit: int = Query(20, ge=5, le=100, description="Number of topics to return"),
    current_user: User = Depends(get_current_user)
) -> List[Dict]:
    """Get trending topics from recent content"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await RagVectorService.get_trending_topics(
        time_range_days=time_range_days,
        limit=limit,
        user_filter=user_filter
    )

@router.post("/rag/summarize-content", response_model=Dict)
async def summarize_content(
    content_ids: List[UUID] = Body(..., embed=True),
    content_type: str = Body(..., embed=True),
    summary_type: str = Body("executive", embed=True),
    max_length: int = Body(500, embed=True, ge=100, le=2000),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Generate AI summary of multiple content items"""
    valid_summary_types = ["executive", "detailed", "key_points", "action_items"]
    if summary_type not in valid_summary_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid summary type. Must be one of: {', '.join(valid_summary_types)}"
        )
    
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return await RagVectorService.summarize_content(
        content_ids=content_ids,
        content_type=content_type,
        summary_type=summary_type,
        max_length=max_length,
        user_filter=user_filter
    )

@router.get("/rag/health-check", response_model=Dict)
async def rag_health_check(
    current_user: User = Depends(admin_required)
) -> Dict:
    """Check RAG system health and statistics (admin only)"""
    return await RagVectorService.get_health_status()

@router.post("/rag/optimize-index", response_model=Dict)
async def optimize_rag_index(
    current_user: User = Depends(admin_required)
) -> Dict:
    """Optimize RAG vector index (admin only)"""
    return await RagVectorService.optimize_index()
