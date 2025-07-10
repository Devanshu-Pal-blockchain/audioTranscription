from typing import Dict
from fastapi import APIRouter, Depends, HTTPException, status
from models.user import User
from service.auth_service import admin_required
from vto_migration import VTOMigration

router = APIRouter()

@router.post("/migration/run-vto-migration", response_model=Dict)
async def run_vto_migration(
    current_user: User = Depends(admin_required)
) -> Dict:
    """Run the VTO system migration (admin only)"""
    migration = VTOMigration()
    result = await migration.run_full_migration()
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {result.get('error', 'Unknown error')}"
        )
    
    return result

@router.get("/migration/validate-vto", response_model=Dict)
async def validate_vto_migration(
    current_user: User = Depends(admin_required)
) -> Dict:
    """Validate VTO system migration (admin only)"""
    migration = VTOMigration()
    await migration.initialize()
    result = await migration.validate_migration()
    
    return {
        "validation_results": result,
        "status": "validation_completed"
    }

@router.get("/system/health", response_model=Dict)
async def system_health_check() -> Dict:
    """Get system health status"""
    # Basic health check that doesn't require authentication
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "2.0.0",
        "system": "VTO Meeting Transcription API"
    }
