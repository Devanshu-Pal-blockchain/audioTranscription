import secrets
import string
from uuid import uuid4
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import Dict, List
import pandas as pd
import io
from service.user_service import UserService
from models.user import User
from service.auth_service import admin_required

router = APIRouter()

@router.post("/upload")
async def upload_csv(
    file: UploadFile = File(...),
    current_admin = Depends(admin_required)
):
    """
    Upload CSV file and create users in the users collection. Validates required fields.
    """
    REQUIRED_FIELDS = {"employee_name", "employee_email", "employee_role", "employee_responsibilities", "employee_code", "employee_designation"}
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
        created_users = []
        for row in csv_data:
            # Always generate a UUID for employee_id, ignore any value from CSV
            row.pop("employee_id", None)
            row["employee_id"] = uuid4()

            # Generate a random password
            def generate_password(length=12):
                alphabet = string.ascii_letters + string.digits + string.punctuation
                return ''.join(secrets.choice(alphabet) for _ in range(length))
            row["employee_password"] = generate_password()

            # Normalize employee_role: only 'admin' or 'employee' allowed
            if row.get("employee_role", "").lower() != "admin":
                row["employee_role"] = "employee"
            else:
                row["employee_role"] = "admin"

            # assigned_rocks is optional
            if "assigned_rocks" in row and row["assigned_rocks"]:
                try:
                    row["assigned_rocks"] = [str(r) for r in row["assigned_rocks"].split(",") if r]
                except Exception:
                    row["assigned_rocks"] = []
            else:
                row["assigned_rocks"] = []
            # Create User model
            user = User(**row)
            created = await UserService.create_user(user)
            created_users.append({"email": created.employee_email, "password": row["employee_password"], "designation": row.get("designation")})

        return {
            "message": "CSV uploaded successfully",
            "users_created": created_users,
            "rows_processed": len(created_users)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

