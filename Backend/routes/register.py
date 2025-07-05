from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from service.register_service import get_user_by_username, create_user

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    password: str
    role: str  # 'admin' or 'employee'
    email: str = None

@router.post("/register")
def register_user(user: UserCreate):
    if get_user_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    create_user(user.username, user.password, user.role, user.email)
    return {"message": f"User {user.username} created successfully as {user.role}"}
