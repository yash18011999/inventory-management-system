# schemas/transfers.py
"""
Schemas for Stock Transfers and Stock Adjustments
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import Field
from schemas import BaseSchema, TransferStatusEnum

# =====================================================
# STOCK TRANSFER SCHEMAS
# =====================================================

class StockTransferItemBase(BaseSchema):
    product_id: int
    quantity_requested: int = Field(..., gt=0)
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None

class StockTransferItemCreate(StockTransferItemBase):
    pass

class StockTransferItemResponse(StockTransferItemBase):
    id: int
    stock_transfer_id: int
    quantity_sent: int
    quantity_received: int
    created_at: datetime

class StockTransferBase(BaseSchema):
    from_warehouse_id: int
    to_warehouse_id: int
    transfer_date: date
    expected_date: Optional[date] = None
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None

class StockTransferCreate(StockTransferBase):
    items: List[StockTransferItemCreate] = Field(..., min_items=1)

class StockTransferUpdate(BaseSchema):
    status: Optional[TransferStatusEnum] = None
    expected_date: Optional[date] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None

class StockTransferResponse(StockTransferBase):
    id: int
    transfer_number: str
    status: TransferStatusEnum
    requested_by: int
    approved_by: Optional[int] = None
    received_by: Optional[int] = None
    created_at: datetime
    items: List[StockTransferItemResponse] = []

# =====================================================
# STOCK ADJUSTMENT SCHEMAS
# =====================================================

class StockAdjustmentItemBase(BaseSchema):
    product_id: int
    quantity_before: int = Field(..., ge=0)
    quantity_counted: int = Field(..., ge=0)
    batch_number: Optional[str] = None
    unit_cost: Optional[float] = None
    notes: Optional[str] = None

class StockAdjustmentItemCreate(StockAdjustmentItemBase):
    pass

class StockAdjustmentItemResponse(StockAdjustmentItemBase):
    id: int
    stock_adjustment_id: int
    quantity_adjusted: int
    quantity_after: int
    total_value_change: float
    created_at: datetime

class StockAdjustmentBase(BaseSchema):
    warehouse_id: int
    adjustment_date: date
    reason: str
    notes: Optional[str] = None

class StockAdjustmentCreate(StockAdjustmentBase):
    items: List[StockAdjustmentItemCreate] = Field(..., min_items=1)

class StockAdjustmentUpdate(BaseSchema):
    status: Optional[str] = None
    notes: Optional[str] = None

class StockAdjustmentResponse(StockAdjustmentBase):
    id: int
    adjustment_number: str
    status: str
    created_by: int
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    items: List[StockAdjustmentItemResponse] = []

# =====================================================
# REPORTS SCHEMAS
# =====================================================

class LowStockReport(BaseSchema):
    product_id: int
    sku: str
    product_name: str
    warehouse_id: int
    warehouse_name: str
    quantity_available: int
    reorder_level: int
    reorder_quantity: int

class StockValueReport(BaseSchema):
    warehouse_id: int
    warehouse_name: str
    total_products: int
    total_quantity: int
    total_value: float

class ProductMovementReport(BaseSchema):
    product_id: int
    sku: str
    product_name: str
    movement_type: str
    quantity: int
    warehouse_name: str
    movement_date: datetime
    reference_type: Optional[str] = None
    reference_number: Optional[str] = None