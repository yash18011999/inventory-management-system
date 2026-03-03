# routers/sales_orders.py
"""
Sales Order management endpoints - COMPLETE WORKING VERSION
"""

from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, select
from datetime import date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from database import get_db
from models import User, SalesOrder, SalesOrderItem, Shipment, ShipmentItem
from schemas.orders import (
    SalesOrderCreate, SalesOrderResponse, SalesOrderUpdate,
    ShipmentCreate, ShipmentResponse
)
from services.order_service import SalesOrderService
from services.inventory_service import InventoryService
from core.security import get_current_user

router = APIRouter()


@router.post("/", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    so_data: SalesOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Create a new sales order
    
    Creates SO in DRAFT status. Use /confirm endpoint to reserve stock.
    """
    return await SalesOrderService.create_sales_order(db, so_data, current_user.id)


@router.get("/", response_model=List[SalesOrderResponse])
async def list_sales_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get list of sales orders
    
    - **status**: Filter by status (DRAFT, CONFIRMED, PACKED, SHIPPED, DELIVERED, CANCELLED)
    - **customer_id**: Filter by customer
    """
    query = select(SalesOrder).options(selectinload(SalesOrder.items))
    
    if status_filter:
        query = query.filter(SalesOrder.status == status_filter)
    
    if customer_id:
        query = query.filter(SalesOrder.customer_id == customer_id)
    
    result = await db.execute(
        query.order_by(SalesOrder.created_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().unique().all()


@router.get("/{so_id}", response_model=SalesOrderResponse)
async def get_sales_order(
    so_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a single sales order by ID"""
    so = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so_id)
    )
    so = so.scalars().unique().first()
    if not so:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales order {so_id} not found"
        )
    return so


@router.post("/{so_id}/confirm", response_model=SalesOrderResponse)
async def confirm_sales_order(
    so_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Confirm sales order and reserve stock
    
    Workflow:
    1. Checks stock availability for all items
    2. Reserves stock (quantity_reserved += ordered)
    3. Changes status to CONFIRMED
    
    If insufficient stock, entire transaction is rolled back.
    """
    print(f"Confirming sales order {so_id} by user {current_user.username}")
    return await SalesOrderService.confirm_sales_order(db, so_id, current_user.id)


@router.post("/{so_id}/cancel")
async def cancel_sales_order(
    so_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Cancel sales order and release reserved stock
    """
    so = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == so_id)
    )
    so = so.scalars().unique().first()
    if not so:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales order {so_id} not found"
        )
    
    # Release reservations if order was confirmed
    if so.status == "CONFIRMED":
        for item in so.items:
            try:
                InventoryService.release_reservation(
                    db=db,
                    product_id=item.product_id,
                    warehouse_id=so.warehouse_id,
                    quantity=item.quantity_ordered - item.quantity_shipped
                )
            except:
                # If stock record doesn't exist, continue
                pass
    
    so.status = "CANCELLED"
    await db.commit()
    await db.refresh(so)
    return so


@router.post("/shipments", response_model=ShipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    shipment_data: ShipmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Create shipment and ship order
    
    Workflow:
    1. Creates shipment record
    2. Deducts stock from inventory
    3. Releases reservations
    4. Updates SO status to SHIPPED
    5. Creates stock movements (audit trail)
    """
    return await SalesOrderService.create_shipment(db, shipment_data, current_user.id)


@router.get("/shipments/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(
    shipment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get shipment details"""
    shipment = await db.execute(
        select(Shipment).options(selectinload(Shipment.items)).where(Shipment.id == shipment_id)
    )
    shipment = shipment.scalars().first()
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment {shipment_id} not found"
        )
    return shipment


@router.put("/shipments/{shipment_id}/deliver")
async def mark_as_delivered(
    shipment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Mark shipment as delivered and update SO status"""
    shipment = await db.execute(
        select(Shipment).options(selectinload(Shipment.items)).where(Shipment.id == shipment_id)
    )
    shipment = shipment.scalars().unique().first()
    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment {shipment_id} not found"
        )
    
    shipment.status = "DELIVERED"
    
    # Update sales order
    so = await db.execute(
        select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == shipment.sales_order_id)
    )
    so = so.scalars().unique().first()
    if so:
        so.status = "DELIVERED"
        so.actual_delivery_date = date.today()
    
    await db.commit()
    await db.refresh(shipment, attribute_names=["items", "sales_order"])
    return shipment


@router.get("/shipments/", response_model=List[ShipmentResponse])
async def list_shipments(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user)
):
    """List all shipments"""
    query = select(Shipment).options(selectinload(Shipment.items))
    
    if status_filter:
        query = query.where(Shipment.status == status_filter)
    
    return (await db.execute(query.order_by(Shipment.created_at.desc()).offset(skip).limit(limit))).scalars().unique().all()