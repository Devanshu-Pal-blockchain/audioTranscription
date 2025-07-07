from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from service.auth_service import authenticate_user, create_access_token, Token
from models.user import User

router = APIRouter()

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
    
    # Create access token with user information
    token_data = {
        "sub": str(user.employee_id),
        "role": user.employee_role,
        "email": user.employee_email
    }
    access_token = await create_access_token(data=token_data)
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.employee_role,
        email=user.employee_email
    )
