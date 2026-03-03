from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Category
from schemas import CategoryCreate, CategoryUpdate, CategoryResponse
from core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Create a new category"""
    db_category = Category(**category.model_dump())
    db.add(db_category)
    await db.commit()
    await db.refresh(db_category)
    return db_category


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    parent_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get list of categories
    
    - **parent_id**: Filter by parent category (for hierarchical navigation)
    - **is_active**: Filter by active status
    """
    query = select(Category)
    
    if parent_id is not None:
        query = query.filter(Category.parent_category_id == parent_id)
    
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)
    
    result = await db.execute(query.order_by(Category.sort_order, Category.name).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a single category by ID"""
    category = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = category.scalars().first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found"
        )
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Update a category"""
    category = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = category.scalars().first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found"
        )
    
    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)
    
    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Deactivate a category"""
    category = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = category.scalars().first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found"
        )
    
    category.is_active = False
    await db.commit()
    return None


@router.get("/{category_id}/subcategories", response_model=List[CategoryResponse])
async def get_subcategories(
    category_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get all subcategories of a category"""
    # First check if parent category exists
    parent = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    parent = parent.scalars().first()
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category {category_id} not found"
        )
    
    result = await db.execute(
        select(Category).where(Category.parent_category_id == category_id).order_by(Category.sort_order, Category.name)
    )
    return result.scalars().all()