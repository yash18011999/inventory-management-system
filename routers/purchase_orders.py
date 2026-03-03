# routers/purchase_orders.py
"""
Purchase Order management endpoints
"""

from typing import List, Optional, Annotated
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, PurchaseOrder
from schemas.orders import (
    PurchaseOrderCreate, PurchaseOrderResponse, PurchaseOrderUpdate,
    GRNCreate, GRNResponse
)
from services.order_service import PurchaseOrderService
from core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

router = APIRouter()


@router.post("/", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    po_data: PurchaseOrderCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Create a new purchase order
    
    Creates PO in DRAFT status. Use /send endpoint to send to vendor.
    """
    return await PurchaseOrderService.create_purchase_order(db, po_data, current_user.id)


@router.get("/", response_model=List[PurchaseOrderResponse])
async def list_purchase_orders(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get list of purchase orders
    
    - **status**: Filter by status (DRAFT, SENT, PARTIAL, RECEIVED, CANCELLED)
    """
    return await PurchaseOrderService.get_purchase_orders(
        db=db,
        skip=skip,
        limit=limit,
        status=status
    )


@router.get("/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a single purchase order by ID"""
    return await PurchaseOrderService.get_purchase_order(db, po_id)


@router.put("/{po_id}/status", response_model=PurchaseOrderResponse)
async def update_po_status(
    po_id: int,
    new_status: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Update purchase order status
    
    - **DRAFT** → **SENT**: Send to vendor (requires approval)
    - **SENT** → **PARTIAL**: Some items received
    - **PARTIAL** → **RECEIVED**: All items received
    - **Any** → **CANCELLED**: Cancel order
    """
    return await PurchaseOrderService.update_po_status(
        db=db,
        po_id=po_id,
        new_status=new_status,
        user_id=current_user.id
    )


@router.post("/{po_id}/send", response_model=PurchaseOrderResponse)
async def send_purchase_order(
    po_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Send purchase order to vendor
    
    Changes status from DRAFT to SENT and records approval.
    """
    return await PurchaseOrderService.update_po_status(
        db=db,
        po_id=po_id,
        new_status="SENT",
        user_id=current_user.id
    )


@router.post("/grn", response_model=GRNResponse, status_code=status.HTTP_201_CREATED)
async def receive_goods(
    grn_data: GRNCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Create Goods Received Note (GRN)
    
    Records receipt of goods and updates:
    - Inventory stock levels
    - Purchase order item quantities
    - Purchase order status
    - Stock movements (audit trail)
    """
    return await PurchaseOrderService.receive_goods(db, grn_data, current_user.id)