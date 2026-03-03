# routers/warehouses.py
"""
Warehouse management endpoints - COMPLETE WORKING VERSION
"""

from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Warehouse
from schemas import WarehouseCreate, WarehouseUpdate, WarehouseResponse
from core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()


@router.post("/", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    warehouse: WarehouseCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Create a new warehouse"""
    # Check if warehouse code exists
    existing = await db.execute(
        select(Warehouse).where(Warehouse.code == warehouse.code)
    )
    existing = existing.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Warehouse with code '{warehouse.code}' already exists"
        )
    
    db_warehouse = Warehouse(**warehouse.model_dump())
    db.add(db_warehouse)
    await db.commit()
    await db.refresh(db_warehouse)
    return db_warehouse


@router.get("/", response_model=List[WarehouseResponse])
async def list_warehouses(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Get list of warehouses"""
    query = select(Warehouse)
    
    if is_active is not None:
        query = query.filter(Warehouse.is_active == is_active)
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    warehouse_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a single warehouse by ID"""
    warehouse = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id)
    )
    warehouse = warehouse.scalars().first()
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Warehouse {warehouse_id} not found"
        )
    return warehouse


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: int,
    warehouse_update: WarehouseUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Update a warehouse"""
    warehouse = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id)
    )
    warehouse = warehouse.scalars().first()
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Warehouse {warehouse_id} not found"
        )
    
    update_data = warehouse_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(warehouse, field, value)
    
    await db.commit()
    await db.refresh(warehouse)
    return warehouse


@router.delete("/{warehouse_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warehouse(
    warehouse_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Deactivate a warehouse"""
    warehouse = await db.execute(
        select(Warehouse).where(Warehouse.id == warehouse_id)
    )
    warehouse = warehouse.scalars().first()
    if not warehouse:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Warehouse {warehouse_id} not found"
        )
    
    warehouse.is_active = False
    await db.commit()
    return None