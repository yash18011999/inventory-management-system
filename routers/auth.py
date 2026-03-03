from datetime import datetime, timedelta, UTC
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated
from database import get_db
from models import User, Role
from schemas import UserCreate, UserLogin, Token, UserResponse
from config import settings
from core.security import (
    create_access_token,
    get_password_hash,
    get_current_user,
    verify_password
)

import jwt
from pwdlib import PasswordHash

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    # Check if user already exists
    existing_user = await db.execute(select(User).filter(User.username == user.username))
    existing_user = existing_user.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    existing_email = await db.execute(select(User).filter(User.email == user.email))
    existing_email = existing_email.scalars().first()
    
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if len(user.password) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too long (max 72 characters)"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        organization_id=user.organization_id,
        role_id=user.role_id,
        email=user.email,
        username=user.username,
        password_hash=hashed_password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        is_active=user.is_active
    )
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)]
):

    """Login and get access token"""
    result = await db.execute(select(User).filter(User.username == form_data.username))
    db_user = result.scalars().first()

    if not db_user or not verify_password(form_data.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(db_user.id)},
        expires_delta=access_token_expires
    )
    
    # Update last login
    db_user.last_login = datetime.now(UTC)
    await db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": db_user
    }


@router.get("/me", response_model=UserResponse)
# async def get_current_user_info(current_user: User = Depends(get_current_user)):
async def get_current_user_info(current_user: Annotated[User, Depends(get_current_user)]):
    """Get current user information"""
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout (client should discard token)"""
    return {"message": "Successfully logged out"}