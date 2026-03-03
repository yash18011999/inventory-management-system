from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import ProductCreate, ProductUpdate, ProductResponse, ProductWithStock
from services.product_service import ProductService
from core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Create a new product"""
    return await ProductService.create_product(db, product, current_user.id)


@router.get("/", response_model=List[ProductResponse])
async def list_products(
    db: Annotated[AsyncSession,Depends(get_db)],
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    search: Optional[str] = Query(None, description="Search by name, SKU, or barcode"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of products with filters
    
    - **search**: Search by name, SKU
    - **category_id**: Filter by category
    - **is_active**: Filter by active status
    """
    return await ProductService.get_products(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        is_active=is_active
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a single product by ID"""
    return await ProductService.get_product(db, product_id)


@router.get("/sku/{sku}", response_model=ProductResponse)
async def get_product_by_sku(
    sku: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a product by SKU"""
    return await ProductService.get_product_by_sku(db, sku)


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    db: Annotated[AsyncSession,Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Update a product"""
    return await ProductService.update_product(db, product_id, product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) a product"""
    await ProductService.delete_product(db, product_id)
    return None


@router.get("/{product_id}/stock")
async def get_product_stock(
    product_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get stock levels for a product across all warehouses"""
    return await ProductService.get_product_stock(db, product_id)