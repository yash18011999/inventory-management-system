"""
Willb e following schemas pattern: Base -> Create -> Update -> Response as per the fastapai
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum

# ENUMS

class OrderStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PARTIAL = "PARTIAL"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"

class SalesOrderStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PaymentStatusEnum(str, Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"

class TransferStatusEnum(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class MovementTypeEnum(str, Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"
    TRANSFER = "TRANSFER"

class PriorityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

# BASE SCHEMAS

class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        use_enum_values = True

# USER & AUTH SCHEMAS

class UserBase(BaseSchema):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=200)
    organization_id: int
    role_id: int = 3  # Default to 'STAFF'

class UserUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    organization_id: int
    role_id: int
    email_verified: bool
    created_at: datetime
    
class UserLogin(BaseSchema):
    username: str
    password: str

class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenData(BaseSchema):
    user_id: Optional[int] = None

# ORGANIZATION SCHEMAS

class OrganizationBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseSchema):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

class OrganizationResponse(OrganizationBase):
    id: int
    is_active: bool
    created_at: datetime


# CATEGORY SCHEMAS

class CategoryBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    parent_category_id: Optional[int] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_category_id: Optional[int] = None
    is_active: Optional[bool] = None

class CategoryResponse(CategoryBase):
    id: int
    is_active: bool
    created_at: datetime


# PRODUCT SCHEMAS

class ProductBase(BaseSchema):
    sku: str = Field(..., min_length=1, max_length=100)
    barcode: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None
    unit_of_measure: str = "pcs"
    weight: Optional[float] = None
    cost_price: float = Field(default=0.0, ge=0)
    selling_price: float = Field(default=0.0, ge=0)
    min_stock_level: int = Field(default=0, ge=0)
    max_stock_level: int = Field(default=1000, ge=0)
    reorder_level: int = Field(default=10, ge=0)
    reorder_quantity: int = Field(default=50, ge=0)
    is_serialized: bool = False
    is_batch_tracked: bool = False

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    cost_price: Optional[float] = Field(None, ge=0)
    selling_price: Optional[float] = Field(None, ge=0)
    reorder_level: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

class ProductResponse(ProductBase):
    id: int
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

class ProductWithStock(ProductResponse):
    total_stock: int = 0
    total_available: int = 0
    total_reserved: int = 0

# WAREHOUSE SCHEMAS

class WarehouseBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

class WarehouseCreate(WarehouseBase):
    organization_id: int

class WarehouseUpdate(BaseSchema):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class WarehouseResponse(WarehouseBase):
    id: int
    organization_id: int
    is_active: bool
    created_at: datetime

# INVENTORY SCHEMAS

class InventoryStockBase(BaseSchema):
    product_id: int
    warehouse_id: int
    quantity_on_hand: int = Field(default=0, ge=0)
    quantity_reserved: int = Field(default=0, ge=0)
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None
    manufacture_date: Optional[date] = None
    expiry_date: Optional[date] = None
    unit_cost: Optional[float] = None

class InventoryStockCreate(InventoryStockBase):
    pass

class InventoryStockUpdate(BaseSchema):
    quantity_on_hand: Optional[int] = Field(None, ge=0)
    quantity_reserved: Optional[int] = Field(None, ge=0)
    unit_cost: Optional[float] = None

class InventoryStockResponse(InventoryStockBase):
    id: int
    quantity_available: int
    total_value: float
    created_at: datetime
    updated_at: Optional[datetime] = None

class StockMovementBase(BaseSchema):
    product_id: int
    warehouse_id: int
    movement_type: MovementTypeEnum
    quantity: int
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    reference_number: Optional[str] = None
    batch_number: Optional[str] = None
    serial_number: Optional[str] = None
    unit_cost: Optional[float] = None
    notes: Optional[str] = None

class StockMovementCreate(StockMovementBase):
    pass

class StockMovementResponse(StockMovementBase):
    id: int
    created_by: int
    movement_date: datetime
    created_at: datetime

# VENDOR SCHEMAS

class VendorBase(BaseSchema):
    vendor_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    currency: str = "USD"

class VendorCreate(VendorBase):
    organization_id: int

class VendorUpdate(BaseSchema):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class VendorResponse(VendorBase):
    id: int
    organization_id: int
    is_active: bool
    created_at: datetime

# CUSTOMER SCHEMAS

class CustomerBase(BaseSchema):
    customer_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    billing_address: Optional[str] = None
    shipping_address: Optional[str] = None
    payment_terms: Optional[str] = None
    credit_limit: Optional[float] = Field(None, ge=0)

class CustomerCreate(CustomerBase):
    organization_id: int

class CustomerUpdate(BaseSchema):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class CustomerResponse(CustomerBase):
    id: int
    organization_id: int
    outstanding_balance: float
    is_active: bool
    created_at: datetime

__all__ = [
    "UserCreate", "UserUpdate", "UserResponse", "UserLogin", "Token", "TokenData",
    "OrganizationCreate", "OrganizationUpdate", "OrganizationResponse",
    "CategoryBase", "CategoryCreate", "CategoryUpdate", "CategoryResponse",
    "ProductBase", "ProductCreate", "ProductUpdate", "ProductResponse", "ProductWithStock",
    "WarehouseBase", "WarehouseCreate", "WarehouseUpdate", "WarehouseResponse",
    "InventoryStockBase", "InventoryStockCreate", "InventoryStockUpdate", "InventoryStockResponse",
    "StockMovementBase", "StockMovementCreate", "StockMovementResponse",
    "VendorBase", "VendorCreate", "VendorUpdate", "VendorResponse",
    "CustomerBase", "CustomerCreate", "CustomerUpdate", "CustomerResponse"
]
