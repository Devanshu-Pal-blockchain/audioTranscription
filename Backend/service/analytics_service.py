from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorCollection
from .db import get_database

class AnalyticsService:
    @staticmethod
    async def get_collection(collection_name: str) -> AsyncIOMotorCollection:
        """Get specified collection"""
        db = await get_database()
        return db[collection_name]

    @staticmethod
    async def get_completion_statistics(quarter_id: Optional[UUID] = None, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get completion statistics based on status fields"""
        
        # Rocks completion statistics
        rocks_collection = await AnalyticsService.get_collection("rocks")
        rock_query = {}
        if quarter_id:
            rock_query["quarter_id"] = quarter_id
        if user_id:
            rock_query["assigned_to_id"] = str(user_id)
        
        # Aggregate rock completion by status
        rock_pipeline = [
            {"$match": rock_query},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        rock_stats = {}
        async for result in rocks_collection.aggregate(rock_pipeline):
            rock_stats[result["_id"]] = result["count"]
        
        # Milestones completion statistics
        milestones_collection = await AnalyticsService.get_collection("milestones")
        milestone_query = {}
        if quarter_id:
            # Join with rocks to filter by quarter
            milestone_pipeline = [
                {
                    "$lookup": {
                        "from": "rocks",
                        "localField": "parent_rock_id",
                        "foreignField": "rock_id",
                        "as": "rock_info"
                    }
                },
                {"$unwind": "$rock_info"},
                {"$match": {"rock_info.quarter_id": quarter_id}},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
        else:
            milestone_pipeline = [
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
        
        milestone_stats = {}
        async for result in milestones_collection.aggregate(milestone_pipeline):
            milestone_stats[result["_id"]] = result["count"]
        
        # ToDos completion statistics
        todos_collection = await AnalyticsService.get_collection("todos")
        todo_query = {}
        if user_id:
            todo_query["owner_id"] = user_id
        
        todo_pipeline = [
            {"$match": todo_query},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]
        
        todo_stats = {}
        async for result in todos_collection.aggregate(todo_pipeline):
            todo_stats[result["_id"]] = result["count"]
        
        # Issues completion statistics
        issues_collection = await AnalyticsService.get_collection("issues")
        issue_query = {}
        if quarter_id:
            # Join with meetings to filter by quarter
            issue_pipeline = [
                {
                    "$lookup": {
                        "from": "meetings",
                        "localField": "meeting_id",
                        "foreignField": "meeting_id",
                        "as": "meeting_info"
                    }
                },
                {"$unwind": "$meeting_info"},
                {"$match": {"meeting_info.quarter_id": quarter_id}},
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
        else:
            issue_pipeline = [
                {"$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }}
            ]
        
        issue_stats = {}
        async for result in issues_collection.aggregate(issue_pipeline):
            issue_stats[result["_id"]] = result["count"]
        
        return {
            "rocks": rock_stats,
            "milestones": milestone_stats,
            "todos": todo_stats,
            "issues": issue_stats
        }

    @staticmethod
    async def calculate_completion_rates(quarter_id: Optional[UUID] = None, user_id: Optional[UUID] = None) -> Dict[str, float]:
        """Calculate completion rates based on status counts"""
        stats = await AnalyticsService.get_completion_statistics(quarter_id, user_id)
        
        rates = {}
        
        for entity_type, status_counts in stats.items():
            total = sum(status_counts.values())
            if total > 0:
                if entity_type in ["rocks", "milestones", "todos"]:
                    completed = status_counts.get("completed", 0)
                elif entity_type == "issues":
                    completed = status_counts.get("resolved", 0)
                else:
                    completed = 0
                
                rates[entity_type] = round((completed / total) * 100, 2)
            else:
                rates[entity_type] = 0.0
        
        return rates

    @staticmethod
    async def get_rock_progress_summary(quarter_id: Optional[UUID] = None, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get rock progress summary with calculated percentages"""
        rocks_collection = await AnalyticsService.get_collection("rocks")
        milestones_collection = await AnalyticsService.get_collection("milestones")
        
        # Get rocks
        rock_query = {}
        if quarter_id:
            rock_query["quarter_id"] = quarter_id
        if user_id:
            rock_query["assigned_to_id"] = str(user_id)
        
        rocks = await rocks_collection.find(rock_query).to_list(length=None)
        
        rock_progress = []
        for rock in rocks:
            # Calculate percentage completion from milestones
            total_milestones = await milestones_collection.count_documents({"parent_rock_id": rock["rock_id"]})
            completed_milestones = await milestones_collection.count_documents({
                "parent_rock_id": rock["rock_id"],
                "status": "completed"
            })
            
            percentage_completion = (completed_milestones / total_milestones * 100) if total_milestones > 0 else 0
            
            rock_progress.append({
                "rock_id": rock["rock_id"],
                "rock_name": rock.get("rock_name", ""),
                "rock_type": rock.get("rock_type", ""),
                "status": rock.get("status", ""),
                "assigned_to": rock.get("assigned_to_name", ""),
                "total_milestones": total_milestones,
                "completed_milestones": completed_milestones,
                "percentage_completion": round(percentage_completion, 2),
                "measurable_success": rock.get("measurable_success", "")
            })
        
        return {
            "rocks": rock_progress,
            "summary": await AnalyticsService.calculate_completion_rates(quarter_id, user_id)
        }

    @staticmethod
    async def get_meeting_analytics(quarter_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get meeting analytics and insights"""
        meetings_collection = await AnalyticsService.get_collection("meetings")
        issues_collection = await AnalyticsService.get_collection("issues")
        todos_collection = await AnalyticsService.get_collection("todos")
        
        # Meeting type distribution
        meeting_query = {}
        if quarter_id:
            meeting_query["quarter_id"] = quarter_id
        
        meeting_pipeline = [
            {"$match": meeting_query},
            {"$group": {
                "_id": "$meeting_type",
                "count": {"$sum": 1},
                "avg_duration": {"$avg": "$duration_minutes"}
            }}
        ]
        
        meeting_types = {}
        async for result in meetings_collection.aggregate(meeting_pipeline):
            meeting_types[result["_id"]] = {
                "count": result["count"],
                "avg_duration": round(result.get("avg_duration", 0), 2)
            }
        
        # Issues generated per meeting type
        issue_pipeline = [
            {
                "$lookup": {
                    "from": "meetings",
                    "localField": "meeting_id",
                    "foreignField": "meeting_id",
                    "as": "meeting_info"
                }
            },
            {"$unwind": "$meeting_info"},
            {"$group": {
                "_id": "$meeting_info.meeting_type",
                "total_issues": {"$sum": 1},
                "resolved_issues": {
                    "$sum": {"$cond": [{"$eq": ["$status", "resolved"]}, 1, 0]}
                }
            }}
        ]
        
        issue_by_meeting = {}
        async for result in issues_collection.aggregate(issue_pipeline):
            issue_by_meeting[result["_id"]] = {
                "total_issues": result["total_issues"],
                "resolved_issues": result["resolved_issues"],
                "resolution_rate": round((result["resolved_issues"] / result["total_issues"]) * 100, 2)
            }
        
        # ToDos generated per meeting type
        todo_pipeline = [
            {
                "$lookup": {
                    "from": "meetings",
                    "localField": "meeting_id", 
                    "foreignField": "meeting_id",
                    "as": "meeting_info"
                }
            },
            {"$unwind": "$meeting_info"},
            {"$group": {
                "_id": "$meeting_info.meeting_type",
                "total_todos": {"$sum": 1},
                "completed_todos": {
                    "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                }
            }}
        ]
        
        todo_by_meeting = {}
        async for result in todos_collection.aggregate(todo_pipeline):
            todo_by_meeting[result["_id"]] = {
                "total_todos": result["total_todos"],
                "completed_todos": result["completed_todos"],
                "completion_rate": round((result["completed_todos"] / result["total_todos"]) * 100, 2)
            }
        
        return {
            "meeting_distribution": meeting_types,
            "issues_by_meeting_type": issue_by_meeting,
            "todos_by_meeting_type": todo_by_meeting
        }

    @staticmethod
    async def get_user_performance_metrics(user_id: UUID, quarter_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get individual user performance metrics"""
        
        # Get completion rates for user
        completion_rates = await AnalyticsService.calculate_completion_rates(quarter_id, user_id)
        
        # Get rock progress
        rock_progress = await AnalyticsService.get_rock_progress_summary(quarter_id, user_id)
        
        # Get todo statistics
        todos_collection = await AnalyticsService.get_collection("todos")
        todo_query = {"owner_id": user_id}
        
        total_todos = await todos_collection.count_documents(todo_query)
        completed_todos = await todos_collection.count_documents({**todo_query, "status": "completed"})
        overdue_todos = await todos_collection.count_documents({
            **todo_query,
            "deadline": {"$lt": datetime.utcnow()},
            "status": {"$ne": "completed"}
        })
        
        # Get milestone completion for user's rocks
        milestones_collection = await AnalyticsService.get_collection("milestones")
        user_rocks = [rock["rock_id"] for rock in rock_progress["rocks"]]
        
        total_milestones = await milestones_collection.count_documents({"parent_rock_id": {"$in": user_rocks}})
        completed_milestones = await milestones_collection.count_documents({
            "parent_rock_id": {"$in": user_rocks},
            "status": "completed"
        })
        
        return {
            "user_id": str(user_id),
            "completion_rates": completion_rates,
            "rock_progress": rock_progress,
            "todo_stats": {
                "total": total_todos,
                "completed": completed_todos,
                "overdue": overdue_todos,
                "completion_rate": round((completed_todos / total_todos * 100), 2) if total_todos > 0 else 0
            },
            "milestone_stats": {
                "total": total_milestones,
                "completed": completed_milestones,
                "completion_rate": round((completed_milestones / total_milestones * 100), 2) if total_milestones > 0 else 0
            }
        }

    @staticmethod
    async def get_quarterly_trends(quarter_ids: List[UUID]) -> Dict[str, Any]:
        """Get trends across multiple quarters"""
        trends = {
            "rock_completion_trends": [],
            "issue_resolution_trends": [],
            "todo_completion_trends": [],
            "milestone_completion_trends": []
        }
        
        for quarter_id in quarter_ids:
            quarter_stats = await AnalyticsService.get_completion_statistics(quarter_id)
            quarter_rates = await AnalyticsService.calculate_completion_rates(quarter_id)
            
            trends["rock_completion_trends"].append({
                "quarter_id": str(quarter_id),
                "completion_rate": quarter_rates.get("rocks", 0)
            })
            
            trends["issue_resolution_trends"].append({
                "quarter_id": str(quarter_id),
                "resolution_rate": quarter_rates.get("issues", 0)
            })
            
            trends["todo_completion_trends"].append({
                "quarter_id": str(quarter_id),
                "completion_rate": quarter_rates.get("todos", 0)
            })
            
            trends["milestone_completion_trends"].append({
                "quarter_id": str(quarter_id),
                "completion_rate": quarter_rates.get("milestones", 0)
            })
        
        return trends

    @staticmethod
    async def get_vto_health_score(quarter_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Calculate overall VTO system health score"""
        completion_rates = await AnalyticsService.calculate_completion_rates(quarter_id)
        
        # Weighted health score calculation
        weights = {
            "rocks": 0.4,      # Rocks are most important
            "milestones": 0.3,  # Milestones show progress
            "todos": 0.2,      # ToDos show execution
            "issues": 0.1      # Issues show problem resolution
        }
        
        health_score = 0
        for entity, rate in completion_rates.items():
            if entity in weights:
                health_score += rate * weights[entity]
        
        # Determine health status
        if health_score >= 80:
            health_status = "excellent"
        elif health_score >= 60:
            health_status = "good"
        elif health_score >= 40:
            health_status = "fair"
        else:
            health_status = "needs_attention"
        
        return {
            "health_score": round(health_score, 2),
            "health_status": health_status,
            "completion_rates": completion_rates,
            "recommendations": await AnalyticsService._generate_recommendations(completion_rates)
        }

    @staticmethod
    async def _generate_recommendations(completion_rates: Dict[str, float]) -> List[str]:
        """Generate recommendations based on completion rates"""
        recommendations = []
        
        if completion_rates.get("rocks", 0) < 50:
            recommendations.append("Focus on rock completion - consider breaking down rocks into smaller milestones")
        
        if completion_rates.get("milestones", 0) < 60:
            recommendations.append("Improve milestone tracking - set more frequent check-ins")
        
        if completion_rates.get("todos", 0) < 70:
            recommendations.append("Better todo management - consider shorter deadlines or clearer priorities")
        
        if completion_rates.get("issues", 0) < 80:
            recommendations.append("Improve issue resolution process - implement regular IDS sessions")
        
        return recommendations
