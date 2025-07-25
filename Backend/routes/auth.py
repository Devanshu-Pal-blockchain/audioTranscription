from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from service.auth_service import authenticate_user, create_access_token, Token
from service.user_service import UserService
from models.user import User

router = APIRouter()

@router.post("/register-admin", response_model=User)
async def register_admin(user: User) -> User:
    """Register an admin user."""
    # Force role to be admin
    user.employee_role = "admin"
    
    # Create the admin user
    created_user = await UserService.create_user(user)
    if not created_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create admin user"
        )
    return created_user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """Login endpoint that returns a JWT token"""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch all assigned rocks and their quarter ids
    from service.rock_service import RockService
    assigned_rocks = []
    if user.assigned_rocks:
        rocks = await RockService.get_rocks_by_user(user.employee_id)
        for rock in rocks:
            assigned_rocks.append({
                "rock_id": str(rock.rock_id),
                "quarter_id": str(rock.quarter_id)
            })
    # Create access token with user information and assigned rocks
    token_data = {
        "sub": str(user.employee_id),
        "role": user.employee_role,
        "email": user.employee_email,
        "assigned_rocks": assigned_rocks
    }
    access_token = await create_access_token(data=token_data)

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.employee_role,
        email=user.employee_email
    )
