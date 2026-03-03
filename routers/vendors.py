# routers/vendors.py
"""
Vendor management endpoints
"""

from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Vendor
from schemas import VendorCreate, VendorUpdate, VendorResponse
from core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()


@router.post("/", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor: VendorCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Create a new vendor"""
    # Check if vendor code exists
    existing = await db.execute(
        select(Vendor).where(Vendor.vendor_code == vendor.vendor_code)
    )
    existing = existing.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vendor with code '{vendor.vendor_code}' already exists"
        )
    
    db_vendor = Vendor(**vendor.dict())
    db.add(db_vendor)
    await db.commit()
    await db.refresh(db_vendor)
    return db_vendor


@router.get("/", response_model=List[VendorResponse])
async def list_vendors(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Get list of vendors"""
    query = select(Vendor)
    
    if search:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Vendor.name.ilike(f"%{search}%"),
                Vendor.vendor_code.ilike(f"%{search}%"),
                Vendor.email.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(Vendor.is_active == is_active)
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{vendor_id}", response_model=VendorResponse)
async def get_vendor(
    vendor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a single vendor by ID"""
    vendor = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = vendor.scalars().first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found"
        )
    return vendor


@router.put("/{vendor_id}", response_model=VendorResponse)
async def update_vendor(
    vendor_id: int,
    vendor_update: VendorUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Update a vendor"""
    vendor = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = vendor.scalars().first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found"
        )
    
    update_data = vendor_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)
    
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Deactivate a vendor"""
    vendor = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = vendor.scalars().first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found"
        )
    
    vendor.is_active = False
    await db.commit()
    return None