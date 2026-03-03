# schemas/orders.py
"""
Schemas for Purchase Orders and Sales Orders
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from schemas import BaseSchema, OrderStatusEnum, SalesOrderStatusEnum, PaymentStatusEnum, PriorityEnum

# =====================================================
# PURCHASE ORDER SCHEMAS
# =====================================================

class PurchaseOrderItemBase(BaseSchema):
    product_id: int
    line_number: int
    quantity_ordered: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    tax_rate: float = Field(default=0.0, ge=0)
    discount_percentage: float = Field(default=0.0, ge=0, le=100)
    discount_amount: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

class PurchaseOrderItemResponse(PurchaseOrderItemBase):
    id: int
    purchase_order_id: int
    quantity_received: int
    quantity_pending: int
    line_total: float
    created_at: datetime

class PurchaseOrderBase(BaseSchema):
    vendor_id: int
    warehouse_id: int
    order_date: date
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    terms_and_conditions: Optional[str] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    items: List[PurchaseOrderItemCreate] = Field(..., min_items=1)

class PurchaseOrderUpdate(BaseSchema):
    expected_delivery_date: Optional[date] = None
    status: Optional[OrderStatusEnum] = None
    notes: Optional[str] = None

class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    po_number: str
    status: OrderStatusEnum
    payment_status: PaymentStatusEnum
    subtotal: float
    tax_amount: float
    shipping_cost: float
    total_amount: float
    created_by: int
    created_at: datetime
    items: List[PurchaseOrderItemResponse] = []

# =====================================================
# GOODS RECEIVED NOTE SCHEMAS
# =====================================================

class GRNItemBase(BaseSchema):
    product_id: int
    po_item_id: int
    quantity_received: int = Field(..., gt=0)
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    condition: str = "GOOD"

class GRNItemCreate(GRNItemBase):
    pass

class GRNItemResponse(GRNItemBase):
    id: int
    grn_id: int
    created_at: datetime

class GRNBase(BaseSchema):
    purchase_order_id: int
    warehouse_id: int
    received_date: date
    notes: Optional[str] = None

class GRNCreate(GRNBase):
    items: List[GRNItemCreate] = Field(..., min_items=1)

class GRNResponse(GRNBase):
    id: int
    grn_number: str
    status: str
    received_by: int
    created_at: datetime
    items: List[GRNItemResponse] = []

# =====================================================
# SALES ORDER SCHEMAS
# =====================================================

class SalesOrderItemBase(BaseSchema):
    product_id: int
    line_number: int
    quantity_ordered: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    tax_rate: float = Field(default=0.0, ge=0)
    discount_percentage: float = Field(default=0.0, ge=0, le=100)
    discount_amount: float = Field(default=0.0, ge=0)
    notes: Optional[str] = None

class SalesOrderItemCreate(SalesOrderItemBase):
    pass

class SalesOrderItemResponse(SalesOrderItemBase):
    id: int
    sales_order_id: int
    quantity_shipped: int
    quantity_pending: int
    line_total: float
    created_at: datetime

class SalesOrderBase(BaseSchema):
    customer_id: int
    warehouse_id: int
    order_date: date
    expected_delivery_date: Optional[date] = None
    priority: PriorityEnum = PriorityEnum.MEDIUM
    shipping_method: Optional[str] = None
    customer_po_number: Optional[str] = None
    notes: Optional[str] = None

class SalesOrderCreate(SalesOrderBase):
    items: List[SalesOrderItemCreate] = Field(..., min_items=1)

class SalesOrderUpdate(BaseSchema):
    expected_delivery_date: Optional[date] = None
    status: Optional[SalesOrderStatusEnum] = None
    priority: Optional[PriorityEnum] = None
    notes: Optional[str] = None

class SalesOrderResponse(SalesOrderBase):
    id: int
    so_number: str
    status: SalesOrderStatusEnum
    payment_status: PaymentStatusEnum
    subtotal: float
    tax_amount: float
    shipping_cost: float
    total_amount: float
    tracking_number: Optional[str] = None
    created_by: int
    created_at: datetime
    items: List[SalesOrderItemResponse] = []

# =====================================================
# SHIPMENT SCHEMAS
# =====================================================

class ShipmentItemBase(BaseSchema):
    product_id: int
    so_item_id: int
    quantity_shipped: int = Field(..., gt=0)
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None

class ShipmentItemCreate(ShipmentItemBase):
    pass

class ShipmentItemResponse(ShipmentItemBase):
    id: int
    shipment_id: int
    created_at: datetime

class ShipmentBase(BaseSchema):
    sales_order_id: int
    warehouse_id: int
    shipment_date: date
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    shipping_cost: float = Field(default=0.0, ge=0)

class ShipmentCreate(ShipmentBase):
    items: List[ShipmentItemCreate] = Field(..., min_items=1)

class ShipmentResponse(ShipmentBase):
    id: int
    shipment_number: str
    status: str
    packed_by: int
    created_at: datetime
    items: List[ShipmentItemResponse] = []