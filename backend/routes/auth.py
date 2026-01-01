from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.database import get_db
from backend.db.models import User
from backend.auth.security import get_password_hash, verify_password, create_access_token
import os
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])

# Shared secret key for both signup and login to restrict access
SECRET_KEY_APP = os.getenv("SECRET_KEY_APP", "SIMPLII-2026-KEY")

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    secret_key: str

class LoginRequest(BaseModel):
    username: str # This can be username or email
    password: str
    secret_key: str

class Token(BaseModel):
    access_token: str
    token_type: str

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    print(f"[AUTH] Signup attempt for: {user_data.username}")
    if user_data.secret_key != SECRET_KEY_APP:
        print(f"[AUTH ERROR] Invalid secret key provided by {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret key"
        )
    
    try:
        # Check if user already exists
        stmt = select(User).where((User.username == user_data.username) | (User.email == user_data.email))
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        hashed_password = get_password_hash(user_data.password)
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        print(f"[AUTH SUCCESS] Created user: {user_data.username}")
        # Create token immediately
        access_token = create_access_token(data={"sub": new_user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH ERROR] Signup failed for {user_data.username}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    print(f"[AUTH] Login attempt for: {login_data.username}")
    # Verify Secret Key first
    if login_data.secret_key != SECRET_KEY_APP:
        print(f"[AUTH ERROR] Invalid secret key in login attempt for {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid secret key"
        )

    try:
        # Check by username or email
        stmt = select(User).where((User.username == login_data.username) | (User.email == login_data.username))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user or not verify_password(login_data.password, user.hashed_password):
            print(f"[AUTH ERROR] Failed login for {login_data.username}: Incorrect credentials")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        print(f"[AUTH SUCCESS] Logged in: {user.username}")
        access_token = create_access_token(data={"sub": user.email})
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH ERROR] Login failed for {login_data.username}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
