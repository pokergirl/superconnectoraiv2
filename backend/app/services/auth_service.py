from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from datetime import datetime, timedelta
from app.core.db import get_database
from app.core.config import settings
from app.core import security
from app.models.user import UserCreate, UserInDB, TokenData, UserRole, UserStatus, AdminUserCreate, PasswordResetRequest, UserPublic
from app.services import invitation_service
import secrets
import string

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_user_by_email(db, email: str):
    return await db.users.find_one({"email": email})

async def create_user(db, user: UserCreate):
    # Validate invitation if provided
    invitation_id = None
    if user.invitation_code:
        invitation = await invitation_service.get_invitation_by_code(db, user.invitation_code)
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invitation code"
            )
        
        if invitation["email"] != user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation email does not match registration email"
            )
        
        # Accept the invitation
        await invitation_service.accept_invitation(db, user.invitation_code)
        invitation_id = invitation["id"]
    else:
        # Check if user is authorized without invitation (for admin bootstrap)
        is_authorized = await invitation_service.is_user_authorized(db, user.email)
        if not is_authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Registration requires a valid invitation"
            )
    
    hashed_password = security.get_password_hash(user.password)
    user_in_db = UserInDB(
        email=user.email,
        hashed_password=hashed_password,
        invitation_id=invitation_id
    )
    
    # Pydantic models must be converted to dicts to be stored in MongoDB
    user_dict = user_in_db.model_dump()
    # Convert UUID to string for MongoDB compatibility
    user_dict["id"] = str(user_dict["id"])
    if user_dict["invitation_id"]:
        user_dict["invitation_id"] = str(user_dict["invitation_id"])
    
    await db.users.insert_one(user_dict)
    return user_dict

async def authenticate_user(db, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user or not security.verify_password(password, user["hashed_password"]):
        return None
    
    # Check if user is still authorized
    if user.get("status") != UserStatus.active.value:
        return None
    
    # Update last login
    await db.users.update_one(
        {"email": email},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    return user

async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_database)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except (JWTError, ValidationError):
        raise credentials_exception
    
    user = await get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    
    # Consistent user status check - same as authenticate_user
    if user.get("status") != UserStatus.active.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is not active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_public = UserPublic(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        status=user["status"],
        is_premium=user["is_premium"],
        must_change_password=user["must_change_password"],
        created_at=user["created_at"],
        last_login=user["last_login"],
    )
    return user_public

def generate_temporary_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

async def create_user_with_otp(db, user_data: AdminUserCreate):
    """Create a new user with a one-time password (admin only)"""
    # Check if user already exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Generate temporary password
    temp_password = generate_temporary_password()
    hashed_password = security.get_password_hash(temp_password)
    
    # Create user with must_change_password flag set to True
    user_in_db = UserInDB(
        email=user_data.email,
        hashed_password=hashed_password,
        must_change_password=True
    )
    
    # Convert to dict for MongoDB storage
    user_dict = user_in_db.model_dump()
    user_dict["id"] = str(user_dict["id"])
    if user_dict["invitation_id"]:
        user_dict["invitation_id"] = str(user_dict["invitation_id"])
    
    await db.users.insert_one(user_dict)
    
    # Return user data with the temporary password
    return user_dict, temp_password

async def create_password_reset_token(email: str) -> str:
    """Create a short-lived token for password reset"""
    expire = datetime.utcnow() + timedelta(minutes=15)  # 15 minute expiry
    to_encode = {"sub": email, "exp": expire, "type": "password_reset"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def verify_password_reset_token(token: str) -> str:
    """Verify password reset token and return email"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid reset token"
            )
        return email
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired reset token"
        )

async def reset_password(db, reset_request: PasswordResetRequest):
    """Reset user password using reset token"""
    email = await verify_password_reset_token(reset_request.reset_token)
    
    # Get user
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Hash new password
    hashed_password = security.get_password_hash(reset_request.new_password)
    
    # Update user password and clear must_change_password flag
    await db.users.update_one(
        {"email": email},
        {
            "$set": {
                "hashed_password": hashed_password,
                "must_change_password": False,
                "last_login": datetime.utcnow()
            }
        }
    )
    
    return {"message": "Password reset successfully"}

async def get_current_admin_user(current_user: UserPublic = Depends(get_current_user)):
    """Dependency to ensure current user is an admin"""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user