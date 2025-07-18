from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from service.auth_service import authenticate_user, create_access_token, Token
from service.user_service import UserService
from models.user import User
from pydantic import BaseModel

router = APIRouter()

# Pydantic models for forgot password
class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str

@router.post("/register-facilitator", response_model=User)
async def register_facilitator(user: User) -> User:
    """Register a facilitator user."""
    # Force role to be facilitator
    user.employee_role = "facilitator"
    
    # Create the facilitator user
    created_user = await UserService.create_user(user)
    if not created_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create facilitator user"
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

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Forgot password endpoint - validates email exists
    Since no email service is required, this just validates the email
    """
    try:
        # Check if user exists with this email
        user = await UserService.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email address"
            )
        
        # Since no email service, just return success
        # In a real application, you would send an email with reset link
        return {
            "message": "Password reset instructions would be sent to your email",
            "email": request.email,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process forgot password request"
        )

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password endpoint - updates password for given email
    """
    try:
        # Check if user exists with this email
        user = await UserService.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No account found with this email address"
            )
        
        # Validate new password (basic validation)
        if len(request.new_password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 6 characters long"
            )
        
        # Update the password
        success = await UserService.update_password(user.employee_id, request.new_password)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        return {
            "message": "Password has been reset successfully",
            "email": request.email,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset password"
        )
