from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from service.auth_service import authenticate_user, create_access_token

router = APIRouter()

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Include role and email in JWT token and response
    email = user.get("email")
    access_token = create_access_token(data={"sub": user["username"], "role": user["role"], "email": email})
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"], "email": email}
