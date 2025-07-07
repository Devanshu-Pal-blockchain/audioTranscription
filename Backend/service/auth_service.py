from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from models.user import User
from .user_service import UserService

# JWT Configuration
SECRET_KEY = "your-secret-key"  # Should be loaded from environment in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme for token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    email: Optional[str] = None

class TokenData(BaseModel):
    employee_id: str
    role: str
    email: Optional[str] = None

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

async def authenticate_user(email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password"""
    user = await UserService.get_user_by_email(email)
    if not user:
        return None
    if not await verify_password(password, user.employee_password):
        return None
    return user

async def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get the current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        employee_id = payload.get("sub")
        role = payload.get("role")
        if not employee_id or not role:
            raise credentials_exception
        token_data = TokenData(
            employee_id=employee_id,
            role=role,
            email=payload.get("email")
        )
    except JWTError:
        raise credentials_exception

    try:
        user = await UserService.get_user(UUID(token_data.employee_id))
        if user is None:
            raise credentials_exception
        return user
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid employee ID format"
        )

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    return current_user

async def admin_required(current_user: User = Depends(get_current_user)) -> User:
    """Verify user has admin role"""
    if current_user.employee_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user
