from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from app.models.user import UserCreate, UserPublic, Token, AdminUserCreate, UserWithOTP, PasswordResetToken, PasswordResetRequest
from app.core.security import create_access_token
from app.core.db import get_database
from app.core import security
from app.services import auth_service

router = APIRouter()

@router.post("/auth/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate,
    db=Depends(get_database),
    current_admin: dict = Depends(auth_service.get_current_admin_user)
):
    """Admin-only endpoint for user registration with invitation codes"""
    db_user = await auth_service.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    new_user = await auth_service.create_user(db, user=user)
    return new_user

@router.post("/auth/login")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_database)):
    user = await auth_service.authenticate_user(db, email=form_data.username, password=form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user must change password
    if user['must_change_password']:
        # Return password reset token instead of access token
        reset_token = await auth_service.create_password_reset_token(user["email"])
        return PasswordResetToken(reset_token=reset_token)
    
    # Normal login flow
    access_token_expires = timedelta(minutes=auth_service.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


@router.post("/auth/reset-password", response_model=Token)
async def reset_password(reset_request: PasswordResetRequest, db=Depends(get_database)):
    await auth_service.reset_password(db, reset_request)
    
    # After successful password reset, log the user in
    email = await auth_service.verify_password_reset_token(reset_request.reset_token)
    access_token_expires = timedelta(minutes=auth_service.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@router.post("/admin/users/create", response_model=UserWithOTP, status_code=status.HTTP_201_CREATED)
async def create_user_with_otp(
    user_data: AdminUserCreate,
    db=Depends(get_database),
    current_admin: dict = Depends(auth_service.get_current_admin_user)
):
    user_dict, temp_password = await auth_service.create_user_with_otp(db, user_data)
    
    # Convert user_dict to UserPublic format and add OTP
    user_public = UserPublic(
        id=user_dict["id"],
        email=user_dict["email"],
        role=user_dict["role"],
        status=user_dict["status"],
        is_premium=user_dict["is_premium"],
        must_change_password=user_dict["must_change_password"],
        created_at=user_dict["created_at"],
        last_login=user_dict.get("last_login")
    )
    
    return UserWithOTP(**user_public.model_dump(), otp=temp_password)

@router.get("/users/me", response_model=UserPublic)
async def read_users_me(current_user: UserPublic = Depends(auth_service.get_current_user)):
    return current_user

@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    # This endpoint is primarily for the client to have a formal endpoint to call.
    # Token invalidation is handled client-side by removing the token.
    return