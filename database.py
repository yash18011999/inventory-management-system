# database.py
"""
Database configuration and session management for Inventory Management System.

This module sets up SQLAlchemy engine and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker, scoped_session, DeclarativeBase
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager

# Load environment variables
# load_dotenv()
DATABASE_URL = "sqlite+aiosqlite:///./inventory.db"

# Create SQLAlchemy engine
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
    )
# SessionLocal = sessionmaker(
#     autocommit=False,
#     autoflush=False,
#     bind=engine
# )


# Base class for declarative models
class Base(DeclarativeBase):
    pass

async def get_db():
    """
    Dependency for FastAPI to get database session.
    
    Usage in FastAPI:
        from fastapi import Depends
        from database import get_db
        
        @app.get("/products")
        def get_products(db: Session = Depends(get_db)):
            return db.query(Product).all()
    """
    async with AsyncSessionLocal() as session:
        yield session

