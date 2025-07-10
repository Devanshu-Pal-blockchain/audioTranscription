from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import quarter, rock, task, user, auth, upload, csv_routes, meeting, ids, milestone, time_slot, analytics, rag_enhanced, migration, session_management, todo
import logging
app = FastAPI(
    title="VTO Meeting Transcription API",
    description="Comprehensive VTO (Vision, Traction, Organizer) API for managing meetings, rocks, issues, solutions, milestones, and analytics",
    version="2.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(quarter.router, tags=["quarters"])
app.include_router(rock.router, tags=["rocks"])
app.include_router(task.router, tags=["tasks"])
app.include_router(user.router, tags=["users"])
app.include_router(upload.router, prefix="/admin", tags=["upload"])
app.include_router(csv_routes.router, prefix="/csv", tags=["csv"])

# New VTO routes
app.include_router(meeting.router, prefix="/api", tags=["meetings"])
app.include_router(ids.router, prefix="/api", tags=["issues-decisions-solutions"])
app.include_router(milestone.router, prefix="/api", tags=["milestones"])
app.include_router(todo.router, prefix="/api", tags=["todos"])
app.include_router(time_slot.router, prefix="/api", tags=["time-slots"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(rag_enhanced.router, prefix="/api/rag", tags=["rag-enhanced"])
app.include_router(session_management.router, tags=["session-management"])
app.include_router(migration.router, prefix="/admin", tags=["migration"])

@app.get("/")
async def root():
    """Root endpoint returning API information"""
    return {
        "name": "VTO Meeting Transcription API",
        "version": "2.0.0",
        "description": "Comprehensive VTO (Vision, Traction, Organizer) API for managing meetings, rocks, issues, solutions, milestones, and analytics",
        "documentation": "/docs",
        "features": [
            "VTO Meeting Management",
            "IDS (Issues, Decisions, Solutions) Workflow", 
            "Rock Tracking (Annual, Company, Individual)",
            "ToDo Management (Parallel to Rocks)",
            "Milestone Management",
            "Audio Recording with Pause/Resume",
            "Session Management",
            "Multiple File Upload Support",
            "Time Slot Analysis",
            "Advanced Analytics & Dashboards",
            "AI-Powered Transcript Analysis"
        ]
    }