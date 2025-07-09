from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from app.core.db import get_database
from app.core.config import settings
from app.core import security
from app.models.user import UserCreate, UserInDB, TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_user_by_email(db, email: str):
    return await db.users.find_one({"email": email})

async def create_user(db, user: UserCreate):
    hashed_password = security.get_password_hash(user.password)
    user_in_db = UserInDB(email=user.email, hashed_password=hashed_password)
    # Pydantic models must be converted to dicts to be stored in MongoDB
    user_dict = user_in_db.model_dump()
    # Convert UUID to string for MongoDB compatibility
    user_dict["id"] = str(user_dict["id"])
    await db.users.insert_one(user_dict)
    return user_dict

async def authenticate_user(db, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user or not security.verify_password(password, user["hashed_password"]):
        return None
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
    return user