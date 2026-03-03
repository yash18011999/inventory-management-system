"""
Inventory and stock management endpoints
"""

from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from database import get_db
from models import User
from schemas import (
    InventoryStockCreate, InventoryStockResponse, InventoryStockUpdate,
    StockMovementResponse
)
from services.inventory_service import InventoryService
from core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter()


@router.get("/stock", response_model=List[InventoryStockResponse])
async def get_inventory_stock(
    db: Annotated[AsyncSession, Depends(get_db)],
    product_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    low_stock_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Get inventory stock levels
    
    - **product_id**: Filter by product
    - **warehouse_id**: Filter by warehouse
    - **low_stock_only**: Only show products below reorder level
    """
    return await InventoryService.get_stock(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        low_stock_only=low_stock_only
    )


@router.get("/stock/{stock_id}", response_model=InventoryStockResponse)
async def get_stock_by_id(
    stock_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get specific stock record"""
    return await InventoryService.get_stock_by_id(db, stock_id)


@router.post("/stock", response_model=InventoryStockResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_stock(
    stock_data: InventoryStockCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Create or update inventory stock
    
    If stock record exists for product+warehouse+batch, quantity will be added.
    Otherwise, a new record is created.
    """
    return await InventoryService.create_or_update_stock(db, stock_data, current_user.id)


@router.post("/stock/adjust")
async def adjust_stock(
    db: Annotated[AsyncSession, Depends(get_db)],
    product_id: int,
    warehouse_id: int,
    quantity_change: int,
    reason: str,
    batch_number: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Adjust stock levels
    
    - **quantity_change**: Positive to add, negative to subtract
    - **reason**: Reason for adjustment
    """
    return await InventoryService.adjust_stock(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity_change=quantity_change,
        reason=reason,
        user_id=current_user.id,
        batch_number=batch_number
    )


@router.post("/stock/reserve")
async def reserve_stock(
    product_id: int,
    warehouse_id: int,
    quantity: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    batch_number: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Reserve stock for an order"""
    return await InventoryService.reserve_stock(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        batch_number=batch_number
    )


@router.post("/stock/release-reservation")
async def release_reservation(
    product_id: int,
    warehouse_id: int,
    quantity: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    batch_number: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Release reserved stock"""
    return await InventoryService.release_reservation(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        batch_number=batch_number
    )


@router.get("/movements", response_model=List[StockMovementResponse])
async def get_stock_movements(
    db: Annotated[AsyncSession, Depends(get_db)],
    product_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    movement_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user)
):
    """
    Get stock movement history
    
    - **product_id**: Filter by product
    - **warehouse_id**: Filter by warehouse
    - **movement_type**: IN, OUT, ADJUST, TRANSFER
    """
    return await InventoryService.get_stock_movements(
        db=db,
        product_id=product_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        limit=limit
    )


@router.get("/reports/low-stock")
async def get_low_stock_report(
    db: Annotated[AsyncSession, Depends(get_db)],
    warehouse_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get products with low stock (below reorder level)
    
    - **warehouse_id**: Filter by warehouse (optional)
    """
    return await InventoryService.get_low_stock_report(db, warehouse_id)