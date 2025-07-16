from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import quarter, rock, task, user, auth, upload, csv_routes, todo, issue, recording, chatbot
import logging
app = FastAPI(
    title="Meeting Transcription API",
    description="API for managing meeting transcriptions, rocks, tasks, and users",
    version="1.0.0"
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
app.include_router(todo.router, tags=["todos"])
app.include_router(issue.router, tags=["issues"])
app.include_router(user.router, tags=["users"])
app.include_router(upload.router, prefix="/admin", tags=["upload"])
app.include_router(recording.router, prefix="/recording", tags=["recording"])
app.include_router(csv_routes.router, prefix="/csv", tags=["csv"])
app.include_router(chatbot.router, prefix="/chatbot", tags=["chatbot"])

@app.get("/")
async def root():
    """Root endpoint returning API information"""
    return {
        "name": "Meeting Transcription API",
        "version": "1.0.0",
        "description": "API for managing meeting transcriptions, rocks, tasks, and users",
        "documentation": "/docs"
    }