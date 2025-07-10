from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from models.user import User
from service.meeting_service import MeetingService
from service.issue_service import IssueService
from service.solution_service import SolutionService
from service.milestone_service import MilestoneService
from service.rock_service import RockService
from service.quarter_service import QuarterService
from service.ids_analysis_service import IDSAnalysisService
from service.auth_service import get_current_user, admin_required

router = APIRouter()

@router.get("/dashboard/overview", response_model=Dict)
async def get_dashboard_overview(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get comprehensive VTO dashboard overview"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    # Get current quarter if not specified
    if not quarter_id:
        current_quarter = await QuarterService.get_current_quarter()
        quarter_id = current_quarter.quarter_id if current_quarter else None
    
    # Gather all dashboard metrics
    overview = {
        "quarter_id": quarter_id,
        "user_role": current_user.employee_role,
        "rocks": await RockService.get_rocks_summary(quarter_id, user_filter),
        "meetings": await MeetingService.get_meeting_type_stats(user_filter),
        "issues": await IssueService.get_issues_summary(quarter_id, user_filter),
        "solutions": await SolutionService.get_solutions_summary(quarter_id, user_filter),
        "milestones": await MilestoneService.get_milestone_stats(quarter_id, None, user_filter),
        "ids_analysis": await IDSAnalysisService.get_ids_summary(quarter_id, user_filter)
    }
    
    return overview

@router.get("/dashboard/vto-health", response_model=Dict)
async def get_vto_health_metrics(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get VTO system health metrics and KPIs"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    # Calculate VTO health scores
    health_metrics = {
        "rock_completion_rate": await RockService.get_completion_rate(quarter_id, user_filter),
        "milestone_on_track_rate": await MilestoneService.get_on_track_rate(quarter_id, user_filter),
        "issue_resolution_rate": await IssueService.get_resolution_rate(quarter_id, user_filter),
        "meeting_frequency_score": await MeetingService.get_frequency_score(quarter_id, user_filter),
        "ids_effectiveness_score": await IDSAnalysisService.get_effectiveness_score(quarter_id, user_filter),
        "overall_vto_score": 0.0  # Will be calculated based on other metrics
    }
    
    # Calculate overall VTO score (weighted average)
    weights = {
        "rock_completion_rate": 0.3,
        "milestone_on_track_rate": 0.25,
        "issue_resolution_rate": 0.2,
        "meeting_frequency_score": 0.15,
        "ids_effectiveness_score": 0.1
    }
    
    overall_score = sum(
        health_metrics[metric] * weight 
        for metric, weight in weights.items()
        if health_metrics[metric] is not None
    )
    health_metrics["overall_vto_score"] = round(overall_score, 2)
    
    return health_metrics

@router.get("/dashboard/rock-progress", response_model=Dict)
async def get_rock_progress_dashboard(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    rock_type: Optional[str] = Query(None, description="Filter by rock type"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get detailed rock progress dashboard"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return {
        "progress_by_type": await RockService.get_progress_by_type(quarter_id, user_filter),
        "completion_trends": await RockService.get_completion_trends(quarter_id, user_filter),
        "at_risk_rocks": await RockService.get_at_risk_rocks(quarter_id, user_filter),
        "top_performers": await RockService.get_top_performers(quarter_id, user_filter),
        "milestone_breakdown": await MilestoneService.get_milestone_breakdown_by_rocks(quarter_id, user_filter)
    }

@router.get("/dashboard/meeting-insights", response_model=Dict)
async def get_meeting_insights_dashboard(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    meeting_type: Optional[str] = Query(None, description="Filter by meeting type"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get meeting insights and analytics dashboard"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return {
        "meeting_frequency": await MeetingService.get_meeting_frequency_analysis(quarter_id, user_filter),
        "attendance_patterns": await MeetingService.get_attendance_patterns(quarter_id, user_filter),
        "duration_analysis": await MeetingService.get_duration_analysis(quarter_id, user_filter),
        "productivity_metrics": await MeetingService.get_productivity_metrics(quarter_id, user_filter),
        "action_item_tracking": await MeetingService.get_action_item_tracking(quarter_id, user_filter)
    }

@router.get("/dashboard/ids-analytics", response_model=Dict)
async def get_ids_analytics_dashboard(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    time_range: int = Query(30, ge=7, le=365, description="Time range in days"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get IDS (Issues, Decisions, Solutions) analytics dashboard"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    return {
        "issue_categories": await IssueService.get_issue_categories_analysis(quarter_id, user_filter),
        "resolution_times": await SolutionService.get_resolution_time_analysis(quarter_id, user_filter),
        "recurring_issues": await IssueService.get_recurring_issues_analysis(quarter_id, user_filter),
        "solution_effectiveness": await SolutionService.get_effectiveness_analysis(quarter_id, user_filter),
        "trend_analysis": await IDSAnalysisService.get_trend_analysis(time_range, user_filter)
    }

@router.get("/reports/quarterly-review", response_model=Dict)
async def generate_quarterly_review(
    quarter_id: UUID,
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Generate comprehensive quarterly review report"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    quarter = await QuarterService.get_quarter(quarter_id)
    if not quarter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quarter not found"
        )
    
    return {
        "quarter_info": quarter,
        "executive_summary": await QuarterService.get_executive_summary(quarter_id, user_filter),
        "rock_achievements": await RockService.get_quarterly_achievements(quarter_id, user_filter),
        "meeting_summary": await MeetingService.get_quarterly_summary(quarter_id, user_filter),
        "issue_resolution": await IssueService.get_quarterly_resolution_summary(quarter_id, user_filter),
        "milestone_completion": await MilestoneService.get_quarterly_completion_summary(quarter_id, user_filter),
        "key_insights": await IDSAnalysisService.get_quarterly_insights(quarter_id, user_filter),
        "recommendations": await QuarterService.get_recommendations(quarter_id, user_filter)
    }

@router.get("/reports/individual-performance", response_model=Dict)
async def get_individual_performance_report(
    user_id: Optional[UUID] = Query(None, description="User ID (admin only, defaults to current user)"),
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get individual performance report"""
    # Non-admin users can only see their own reports
    if current_user.employee_role != "admin":
        user_id = current_user.employee_id
    elif not user_id:
        user_id = current_user.employee_id
    
    return {
        "user_id": user_id,
        "quarter_id": quarter_id,
        "rock_performance": await RockService.get_individual_performance(user_id, quarter_id),
        "meeting_participation": await MeetingService.get_individual_participation(user_id, quarter_id),
        "issue_management": await IssueService.get_individual_management_stats(user_id, quarter_id),
        "milestone_tracking": await MilestoneService.get_individual_tracking_stats(user_id, quarter_id),
        "collaboration_metrics": await get_collaboration_metrics(user_id, quarter_id)
    }

async def get_collaboration_metrics(user_id: UUID, quarter_id: Optional[UUID]) -> Dict:
    """Helper function to calculate collaboration metrics"""
    # This would aggregate cross-service metrics
    return {
        "meetings_attended": await MeetingService.count_user_meetings(user_id, quarter_id),
        "issues_created": await IssueService.count_user_issues_created(user_id, quarter_id),
        "solutions_provided": await SolutionService.count_user_solutions(user_id, quarter_id),
        "milestones_owned": await MilestoneService.count_user_milestones(user_id, quarter_id),
        "collaboration_score": 0.0  # Would be calculated based on various factors
    }

@router.get("/reports/team-dynamics", response_model=Dict)
async def get_team_dynamics_report(
    quarter_id: Optional[UUID] = Query(None, description="Filter by quarter"),
    current_user: User = Depends(admin_required)
) -> Dict:
    """Get team dynamics and collaboration report (admin only)"""
    return {
        "communication_patterns": await MeetingService.get_communication_patterns(quarter_id),
        "workload_distribution": await RockService.get_workload_distribution(quarter_id),
        "cross_functional_collaboration": await get_cross_functional_metrics(quarter_id),
        "knowledge_sharing": await MeetingService.get_knowledge_sharing_metrics(quarter_id),
        "team_health_indicators": await get_team_health_indicators(quarter_id)
    }

async def get_cross_functional_metrics(quarter_id: Optional[UUID]) -> Dict:
    """Helper function to calculate cross-functional collaboration metrics"""
    return {
        "shared_rocks": await RockService.count_shared_rocks(quarter_id),
        "cross_team_issues": await IssueService.count_cross_team_issues(quarter_id),
        "collaborative_solutions": await SolutionService.count_collaborative_solutions(quarter_id),
        "inter_department_meetings": await MeetingService.count_inter_department_meetings(quarter_id)
    }

async def get_team_health_indicators(quarter_id: Optional[UUID]) -> Dict:
    """Helper function to calculate team health indicators"""
    return {
        "issue_escalation_rate": await IssueService.get_escalation_rate(quarter_id),
        "solution_implementation_rate": await SolutionService.get_implementation_rate(quarter_id),
        "meeting_effectiveness_score": await MeetingService.get_effectiveness_score(quarter_id),
        "goal_alignment_score": await RockService.get_alignment_score(quarter_id)
    }

@router.get("/analytics/trends", response_model=Dict)
async def get_trend_analysis(
    metric: str = Query(..., description="Metric to analyze (rocks, issues, meetings, milestones)"),
    time_range: int = Query(90, ge=30, le=365, description="Time range in days"),
    granularity: str = Query("weekly", description="Granularity (daily, weekly, monthly)"),
    current_user: User = Depends(get_current_user)
) -> Dict:
    """Get trend analysis for various VTO metrics"""
    user_filter = None if current_user.employee_role == "admin" else current_user.employee_id
    
    if metric == "rocks":
        return await RockService.get_trend_analysis(time_range, granularity, user_filter)
    elif metric == "issues":
        return await IssueService.get_trend_analysis(time_range, granularity, user_filter)
    elif metric == "meetings":
        return await MeetingService.get_trend_analysis(time_range, granularity, user_filter)
    elif metric == "milestones":
        return await MilestoneService.get_trend_analysis(time_range, granularity, user_filter)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid metric. Supported: rocks, issues, meetings, milestones"
        )

@router.get("/analytics/predictive", response_model=Dict)
async def get_predictive_analytics(
    current_user: User = Depends(admin_required)
) -> Dict:
    """Get predictive analytics and forecasting (admin only)"""
    return {
        "rock_completion_forecast": await RockService.get_completion_forecast(),
        "issue_volume_prediction": await IssueService.get_volume_prediction(),
        "milestone_risk_assessment": await MilestoneService.get_risk_assessment(),
        "quarter_success_probability": await QuarterService.get_success_probability()
    }
