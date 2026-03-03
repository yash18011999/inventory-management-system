# routers/stock_adjustments.py
"""
Stock Adjustment management endpoints
"""

from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database import get_db
from models import User, StockAdjustment, StockAdjustmentItem, InventoryStock, StockMovement, AdjustmentReason
from schemas.transfers import StockAdjustmentCreate, StockAdjustmentResponse, StockAdjustmentUpdate
from core.security import get_current_user
from datetime import date, datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload


router = APIRouter()


async def generate_adjustment_number(db: AsyncSession) -> str:
    """Generate next adjustment number"""
    last_adj = await db.execute(
        select(StockAdjustment).order_by(StockAdjustment.id.desc())
    )
    last_adj = last_adj.scalars().first()
    
    if last_adj and last_adj.adjustment_number:
        try:
            last_num = int(last_adj.adjustment_number.split('-')[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    return f"ADJ-{date.today().strftime('%Y')}-{new_num:05d}"


@router.post("/", response_model=StockAdjustmentResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_adjustment(
    adjustment_data: StockAdjustmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Create a new stock adjustment
    
    Creates adjustment in DRAFT status. Use /approve endpoint to apply adjustment.
    
    Reasons:
    - DAMAGED: Items damaged
    - LOST: Items lost/stolen
    - FOUND: Extra items found
    - EXPIRED: Items expired
    - CORRECTION: Inventory count correction
    - CYCLE_COUNT: Regular cycle count
    - SHRINKAGE: Shrinkage/loss
    - OTHER: Other reasons
    """
    adjustment_number = await generate_adjustment_number(db)
    
    adjustment = StockAdjustment(
        adjustment_number=adjustment_number,
        warehouse_id=adjustment_data.warehouse_id,
        adjustment_date=adjustment_data.adjustment_date,
        reason=adjustment_data.reason,
        notes=adjustment_data.notes,
        status="DRAFT",
        created_by=current_user.id
    )
    
    db.add(adjustment)
    await db.flush()
    
    # Add items
    for item_data in adjustment_data.items:
        item = StockAdjustmentItem(
            stock_adjustment_id=adjustment.id,
            **item_data.dict()
        )
        db.add(item)
    
    await db.commit()
    await db.refresh(adjustment, attribute_names=["items"])
    return adjustment


@router.get("/", response_model=List[StockAdjustmentResponse])
async def list_stock_adjustments(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    warehouse_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get list of stock adjustments"""
    query = select(StockAdjustment).options(selectinload(StockAdjustment.items))
    
    if status:
        query = query.filter(StockAdjustment.status == status)
    
    if warehouse_id:
        query = query.filter(StockAdjustment.warehouse_id == warehouse_id)
    
    result = await db.execute(query.order_by(StockAdjustment.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().unique().all()


@router.get("/{adjustment_id}", response_model=StockAdjustmentResponse)
async def get_stock_adjustment(
    adjustment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a single stock adjustment by ID"""
    adjustment = await db.execute(
        select(StockAdjustment).options(selectinload(StockAdjustment.items)).where(StockAdjustment.id == adjustment_id)
    )
    adjustment = adjustment.scalars().unique().first()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock adjustment {adjustment_id} not found"
        )
    return adjustment


@router.post("/{adjustment_id}/approve", response_model=StockAdjustmentResponse)
async def approve_stock_adjustment(
    adjustment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Approve and apply stock adjustment
    
    Workflow:
    1. Updates inventory quantities based on counted amounts
    2. Creates stock movement records (audit trail)
    3. Changes status to APPROVED
    
    This is the final step that actually modifies inventory levels.
    """
    adjustment = await db.execute(
        select(StockAdjustment).options(selectinload(StockAdjustment.items)).where(StockAdjustment.id == adjustment_id)
    )
    adjustment = adjustment.scalars().unique().first()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adjustment not found"
        )
    
    if adjustment.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adjustment is already {adjustment.status}"
        )
    
    # Process each item
    for item in adjustment.items:
        # Get current stock
        stmt = await db.execute(
            select(InventoryStock).where(
                and_(
                    InventoryStock.product_id == item.product_id,
                    InventoryStock.warehouse_id == adjustment.warehouse_id,
                    InventoryStock.batch_number == item.batch_number if item.batch_number else True
                )
            ).with_for_update()
        )
        stock = stmt.scalars().first()
        
        if not stock:
            # Create new stock record if doesn't exist
            stock = InventoryStock(
                product_id=item.product_id,
                warehouse_id=adjustment.warehouse_id,
                quantity_on_hand=item.quantity_counted,
                batch_number=item.batch_number,
                unit_cost=item.unit_cost
            )
            db.add(stock)
        else:
            # Update existing stock
            stock.quantity_on_hand = item.quantity_counted
        
        # Create stock movement for audit trail
        quantity_change = item.quantity_counted - item.quantity_before
        
        movement = StockMovement(
            product_id=item.product_id,
            warehouse_id=adjustment.warehouse_id,
            movement_type="ADJUST",
            quantity=quantity_change,
            reference_type="ADJUSTMENT",
            reference_id=adjustment.id,
            reference_number=adjustment.adjustment_number,
            batch_number=item.batch_number,
            unit_cost=item.unit_cost,
            notes=f"Adjustment: {adjustment.reason}",
            created_by=current_user.id
        )
        db.add(movement)
    
    adjustment.status = "APPROVED"
    adjustment.approved_by = current_user.id
    adjustment.approved_at = datetime.now(UTC)
    
    await db.commit()
    await db.refresh(adjustment, attribute_names=["items"])
    return adjustment


@router.post("/{adjustment_id}/reject")
async def reject_stock_adjustment(
    adjustment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Reject stock adjustment
    
    Changes status to REJECTED without modifying inventory.
    """
    adjustment = await db.execute(
        select(StockAdjustment).options(selectinload(StockAdjustment.items)).where(StockAdjustment.id == adjustment_id)
    )
    adjustment = adjustment.scalars().unique().first()
    if not adjustment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Adjustment not found"
        )
    
    if adjustment.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Adjustment is already {adjustment.status}"
        )
    
    adjustment.status = "REJECTED"
    adjustment.approved_by = current_user.id
    adjustment.approved_at = datetime.now(UTC)
    
    await db.commit()
    await db.refresh(adjustment, attribute_names=["items"])
    return adjustment