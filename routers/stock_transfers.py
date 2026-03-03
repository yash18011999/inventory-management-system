# routers/stock_transfers.py
"""
Stock Transfer management endpoints
"""

from typing import List, Optional, Annotated
from attr import attrib
from fastapi import APIRouter, Depends, Query, status, HTTPException
from mypy import options
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database import get_db
from models import User, StockTransfer, StockTransferItem, InventoryStock, StockMovement, TransferStatus
from schemas.transfers import StockTransferCreate, StockTransferResponse, StockTransferUpdate
from core.security import get_current_user
from datetime import UTC, date, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload


router = APIRouter()


async def generate_transfer_number(db: AsyncSession) -> str:
    """Generate next transfer number"""
    last_transfer = await db.execute(
        select(StockTransfer).order_by(StockTransfer.id.desc())
    )
    last_transfer = last_transfer.scalars().first()
    
    if last_transfer and last_transfer.transfer_number:
        try:
            last_num = int(last_transfer.transfer_number.split('-')[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    return f"TRANS-{date.today().strftime('%Y')}-{new_num:05d}"


@router.post("/", response_model=StockTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_stock_transfer(
    transfer_data: StockTransferCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Create a new stock transfer
    
    Creates transfer in PENDING status. Use /approve endpoint to start transfer.
    """
    if transfer_data.from_warehouse_id == transfer_data.to_warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="From and To warehouses must be different"
        )
    
    transfer_number = await generate_transfer_number(db)
    
    transfer = StockTransfer(
        transfer_number=transfer_number,
        from_warehouse_id=transfer_data.from_warehouse_id,
        to_warehouse_id=transfer_data.to_warehouse_id,
        transfer_date=transfer_data.transfer_date,
        expected_date=transfer_data.expected_date,
        shipping_method=transfer_data.shipping_method,
        tracking_number=transfer_data.tracking_number,
        notes=transfer_data.notes,
        status="PENDING",
        requested_by=current_user.id
    )
    
    db.add(transfer)
    await db.flush()
    
    # Add items
    for item_data in transfer_data.items:
        item = StockTransferItem(
            stock_transfer_id=transfer.id,
            **item_data.model_dump()
        )
        db.add(item)

    res = await db.execute(
        select(StockTransfer)
        .options(selectinload(StockTransfer.items))
        .where(StockTransfer.id == transfer.id)
    )
    transfer = res.scalars().first()
    await db.commit()
    await db.refresh(transfer, attribute_names=["items"])
    return transfer


@router.get("/", response_model=List[StockTransferResponse])
async def list_stock_transfers(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    from_warehouse_id: Optional[int] = None,
    to_warehouse_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get list of stock transfers"""
    query = select(StockTransfer).options(selectinload(StockTransfer.items))
    
    if status:
        query = query.filter(StockTransfer.status == status)
    
    if from_warehouse_id:
        query = query.filter(StockTransfer.from_warehouse_id == from_warehouse_id)
    
    if to_warehouse_id:
        query = query.filter(StockTransfer.to_warehouse_id == to_warehouse_id)
    
    result = await db.execute(query.order_by(StockTransfer.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().unique().all()


@router.get("/{transfer_id}", response_model=StockTransferResponse)
async def get_stock_transfer(
    transfer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a single stock transfer by ID"""
    transfer = await db.execute(
        select(StockTransfer).options(selectinload(StockTransfer.items)).where(StockTransfer.id == transfer_id)
    )
    transfer = transfer.scalars().unique().first()
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock transfer {transfer_id} not found"
        )
    return transfer


@router.post("/{transfer_id}/approve", response_model=StockTransferResponse)
async def approve_transfer(
    transfer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Approve stock transfer
    
    Changes status from PENDING to APPROVED.
    """
    transfer = await db.execute(
        select(StockTransfer).options(selectinload(StockTransfer.items)).where(StockTransfer.id == transfer_id)
    )
    transfer = transfer.scalars().unique().first()
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock transfer {transfer_id} not found"
        )
    
    if transfer.status != TransferStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transfer is already {transfer.status}"
        )
    
    transfer.status = TransferStatus.APPROVED
    transfer.approved_by = current_user.id
    transfer.approved_at = datetime.now(UTC)
    
    await db.commit()
    await db.refresh(transfer, attribute_names=["items"])
    return transfer


@router.post("/{transfer_id}/send", response_model=StockTransferResponse)
async def send_transfer(
    transfer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Send stock transfer (mark as in transit)
    
    Workflow:
    1. Deducts stock from source warehouse
    2. Adds to in_transit quantity at destination
    3. Creates stock movement records
    4. Changes status to IN_TRANSIT
    """
    transfer = await db.execute(
        select(StockTransfer).options(selectinload(StockTransfer.items)).where(StockTransfer.id == transfer_id)
    )
    transfer = transfer.scalars().unique().first()
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    if transfer.status != TransferStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer must be approved first"
        )
    
    # Process each item
    for item in transfer.items:
        # Check source stock
        stmt = await db.execute(
            select(InventoryStock).where(
                and_(
                    InventoryStock.product_id == item.product_id,
                    InventoryStock.warehouse_id == transfer.from_warehouse_id,
                InventoryStock.batch_number == item.batch_number if item.batch_number else True
            )
        ).with_for_update())
        source_stock = stmt.scalars().first()
        
        if not source_stock or source_stock.quantity_available < item.quantity_requested:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {item.product_id}"
            )
        
        # Deduct from source
        source_stock.quantity_on_hand -= item.quantity_requested
        
        # Add to destination in_transit or create new record
        stmt = await db.execute(
            select(InventoryStock).where(
                and_(
                    InventoryStock.product_id == item.product_id,
                    InventoryStock.warehouse_id == transfer.to_warehouse_id,
                    InventoryStock.batch_number == item.batch_number if item.batch_number else True
                )
        ))
        dest_stock = stmt.scalars().first()
        
        if dest_stock:
            dest_stock.quantity_in_transit += item.quantity_requested
        else:
            dest_stock = InventoryStock(
                product_id=item.product_id,
                warehouse_id=transfer.to_warehouse_id,
                quantity_on_hand=0,
                quantity_in_transit=item.quantity_requested,
                batch_number=item.batch_number
            )
            db.add(dest_stock)
        
        # Create stock movements
        # OUT from source
        movement_out = StockMovement(
            product_id=item.product_id,
            warehouse_id=transfer.from_warehouse_id,
            movement_type="TRANSFER",
            quantity=-item.quantity_requested,
            reference_type="TRANSFER",
            reference_id=transfer.id,
            reference_number=transfer.transfer_number,
            batch_number=item.batch_number,
            created_by=current_user.id
        )
        db.add(movement_out)
        
        # Update item
        item.quantity_sent = item.quantity_requested
    
    transfer.status = TransferStatus.IN_TRANSIT
    
    await db.commit()
    await db.refresh(transfer, attribute_names=["items"])
    return transfer


@router.post("/{transfer_id}/receive", response_model=StockTransferResponse)
async def receive_transfer(
    transfer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """
    Receive stock transfer at destination
    
    Workflow:
    1. Adds stock to destination warehouse
    2. Removes from in_transit
    3. Creates stock movement records
    4. Changes status to COMPLETED
    """
    stmt = select(StockTransfer).options(selectinload(StockTransfer.items)).where(StockTransfer.id == transfer_id)
    result = await db.execute(stmt)
    transfer = result.scalars().unique().first()
    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )
    
    if transfer.status != TransferStatus.IN_TRANSIT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer must be in transit"
        )
    
    # Process each item
    for item in transfer.items:
        stmt = select(InventoryStock).where(
            and_(
                InventoryStock.product_id == item.product_id,
                InventoryStock.warehouse_id == transfer.to_warehouse_id,
                InventoryStock.batch_number == item.batch_number if item.batch_number else True
            )
        )
        result = await db.execute(stmt)
        dest_stock = result.scalars().first()
        
        if dest_stock:
            dest_stock.quantity_on_hand += item.quantity_sent
            dest_stock.quantity_in_transit -= item.quantity_sent
        
        # Create stock movement (IN to destination)
        movement_in = StockMovement(
            product_id=item.product_id,
            warehouse_id=transfer.to_warehouse_id,
            movement_type="TRANSFER",
            quantity=item.quantity_sent,
            reference_type="TRANSFER",
            reference_id=transfer.id,
            reference_number=transfer.transfer_number,
            batch_number=item.batch_number,
            created_by=current_user.id
        )
        db.add(movement_in)
        
        # Update item
        item.quantity_received = item.quantity_sent
    
    transfer.status = TransferStatus.COMPLETED
    transfer.received_by = current_user.id
    transfer.received_at = datetime.now(UTC)
    
    await db.commit()
    await db.refresh(transfer, attribute_names=["items"])
    return transfer