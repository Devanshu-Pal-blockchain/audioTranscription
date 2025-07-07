from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Dict, List
import pandas as pd
import io
from service.meeting_json_service import save_csv_context
from service.auth_service import admin_required

router = APIRouter()

@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    current_admin = Depends(admin_required)
):
    """
    Upload CSV file and assign UUIDs to employees. Validates required fields.
    """
    REQUIRED_FIELDS = {"empId", "name", "email", "role", "responsibilities"}
    try:
        # Read CSV file
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

        # Validate required fields
        missing = REQUIRED_FIELDS - set(df.columns)
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing required fields in CSV: {', '.join(missing)}")

        # Convert DataFrame to list of dictionaries
        csv_data = df.to_dict(orient='records')

        # Save CSV context and assign UUIDs
        context_id = await save_csv_context(csv_data, str(current_admin.employee_id))

        return {
            "message": "CSV uploaded successfully",
            "context_id": context_id,
            "rows_processed": len(csv_data)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/context/{context_id}")
async def get_csv_context(
    context_id: str,
    current_admin = Depends(admin_required)
):
    """
    Get CSV context by ID
    """
    try:
        context = await fetch_csv_context(context_id)
        if not context:
            raise HTTPException(status_code=404, detail="CSV context not found")
            
        return context
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 