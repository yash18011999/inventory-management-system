# Inventory Management System - SQLAlchemy Models
from __future__ import annotations


from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, Date,
    ForeignKey, Enum, CheckConstraint, UniqueConstraint, Index,
    event, func, Computed
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import UTC, datetime, timezone
import enum

from database import Base

# Base = declarative_base()

# ENUMS
class OrderStatus(enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PARTIAL = "PARTIAL"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"

class SalesOrderStatus(enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PaymentStatus(enum.Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    PAID = "PAID"

class TransferStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class AdjustmentReason(enum.Enum):
    DAMAGED = "DAMAGED"
    LOST = "LOST"
    FOUND = "FOUND"
    EXPIRED = "EXPIRED"
    CORRECTION = "CORRECTION"
    CYCLE_COUNT = "CYCLE_COUNT"
    SHRINKAGE = "SHRINKAGE"
    OTHER = "OTHER"

class MovementType(enum.Enum):
    IN = "IN"
    OUT = "OUT"
    ADJUST = "ADJUST"
    TRANSFER = "TRANSFER"


# 1. USER & AUTHENTICATION MODULE
class Organization(Base):
    __tablename__ = 'organizations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    phone = Column(String(50))
    email = Column(String(255))
    tax_id = Column(String(100))
    website = Column(String(255))
    logo_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    users = relationship("User", back_populates="organization")
    warehouses = relationship("Warehouse", back_populates="organization")
    vendors = relationship("Vendor", back_populates="organization")
    customers = relationship("Customer", back_populates="organization")
    
    __table_args__ = (
        Index('idx_org_name', 'name'),
        Index('idx_org_active', 'is_active'),
    )

class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    permissions = Column(Text)  # JSON string
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(50))
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    last_login = Column(DateTime)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    organization = relationship("Organization", back_populates="users")
    role = relationship("Role", back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    created_products = relationship("Product", back_populates="creator", foreign_keys="Product.created_by")
    
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_username', 'username'),
        Index('idx_user_org', 'organization_id'),
    )
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

class UserSession(Base):
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(500), nullable=False, unique=True)
    refresh_token = Column(String(500))
    ip_address = Column(String(50))
    user_agent = Column(Text)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index('idx_session_token', 'token'),
        Index('idx_session_expires', 'expires_at'),
    )


# 2. PRODUCT MANAGEMENT MODULE
class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    parent_category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'))
    image_url = Column(String(500))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # (self-referencing for hierarchy)
    parent = relationship("Category", remote_side=[id], backref="subcategories")
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String(100), nullable=False, unique=True)
    barcode = Column(String(100), unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='SET NULL'))
    
    # Measurement
    unit_of_measure = Column(String(50), default='pcs')
    weight = Column(Float)
    dimensions = Column(String(100))  # LxWxH
    
    # Pricing
    cost_price = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    currency = Column(String(3), default='USD')
    
    # Inventory Control
    min_stock_level = Column(Integer, default=0)
    max_stock_level = Column(Integer, default=1000)
    reorder_level = Column(Integer, default=10)
    reorder_quantity = Column(Integer, default=50)
    
    # Tracking Options
    is_serialized = Column(Boolean, default=False)
    is_batch_tracked = Column(Boolean, default=False)
    is_perishable = Column(Boolean, default=False)
    shelf_life_days = Column(Integer)
    
    # Status & Media
    is_active = Column(Boolean, default=True)
    image_url = Column(String(500))
    
    created_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    category = relationship("Category", back_populates="products")
    creator = relationship("User", back_populates="created_products", foreign_keys=[created_by])
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    inventory_stock = relationship("InventoryStock", back_populates="product", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_product_sku', 'sku'),
        Index('idx_product_barcode', 'barcode'),
        Index('idx_product_name', 'name'),
        Index('idx_product_category', 'category_id'),
        Index('idx_product_active', 'is_active'),
    )

class ProductVariant(Base):
    __tablename__ = 'product_variants'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    variant_name = Column(String(100), nullable=False)
    sku = Column(String(100), nullable=False, unique=True)
    barcode = Column(String(100), unique=True)
    additional_cost = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    product = relationship("Product", back_populates="variants")

class ProductImage(Base):
    __tablename__ = 'product_images'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    image_url = Column(String(500), nullable=False)
    is_primary = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    alt_text = Column(String(255))
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    
    product = relationship("Product", back_populates="images")


# 3. WAREHOUSE MANAGEMENT MODULE
class Warehouse(Base):
    __tablename__ = 'warehouses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    
    # Location
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    
    # Contact
    phone = Column(String(50))
    email = Column(String(255))
    manager_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    
    # Details
    warehouse_type = Column(String(50))
    total_area = Column(Float)
    area_unit = Column(String(20))
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    organization = relationship("Organization", back_populates="warehouses")
    zones = relationship("WarehouseZone", back_populates="warehouse", cascade="all, delete-orphan")
    inventory_stock = relationship("InventoryStock", back_populates="warehouse")
    
    __table_args__ = (
        Index('idx_warehouse_code', 'code'),
        Index('idx_warehouse_org', 'organization_id'),
    )

class WarehouseZone(Base):
    __tablename__ = 'warehouse_zones'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False)
    zone_name = Column(String(100), nullable=False)
    zone_code = Column(String(50), nullable=False)
    description = Column(Text)
    zone_type = Column(String(50))  # receiving, storage, picking, shipping
    temperature_controlled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    warehouse = relationship("Warehouse", back_populates="zones")
    bin_locations = relationship("BinLocation", back_populates="zone", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('warehouse_id', 'zone_code', name='unique_warehouse_zone_code'),
    )

class BinLocation(Base):
    __tablename__ = 'bin_locations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    zone_id = Column(Integer, ForeignKey('warehouse_zones.id', ondelete='CASCADE'), nullable=False)
    aisle = Column(String(20))
    rack = Column(String(20))
    shelf = Column(String(20))
    bin = Column(String(20))
    bin_code = Column(String(50), nullable=False, unique=True)
    capacity = Column(Integer)
    current_utilization = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    zone = relationship("WarehouseZone", back_populates="bin_locations")


# 4. INVENTORY STOCK MODULE
class InventoryStock(Base):
    __tablename__ = 'inventory_stock'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='CASCADE'), nullable=False)
    bin_location_id = Column(Integer, ForeignKey('bin_locations.id', ondelete='SET NULL'))
    
    # Quantities
    quantity_on_hand = Column(Integer, default=0, nullable=False)
    quantity_reserved = Column(Integer, default=0, nullable=False)
    quantity_in_transit = Column(Integer, default=0, nullable=False)
    
    # Tracking
    batch_number = Column(String(100))
    serial_number = Column(String(100))
    manufacture_date = Column(Date)
    expiry_date = Column(Date)
    
    # Costing
    unit_cost = Column(Float)
    
    # Timestamps
    last_counted_at = Column(DateTime)
    last_restocked_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    # Relationships
    product = relationship("Product", back_populates="inventory_stock")
    warehouse = relationship("Warehouse", back_populates="inventory_stock")
    
    # Computed property for quantity_available
    @hybrid_property
    def quantity_available(self):
        return self.quantity_on_hand - self.quantity_reserved
    
    @hybrid_property
    def total_value(self):
        return (self.quantity_on_hand * self.unit_cost) if self.unit_cost else 0
    
    __table_args__ = (
        UniqueConstraint('product_id', 'warehouse_id', 'batch_number', 'serial_number',
                        name='unique_product_warehouse_batch'),
        Index('idx_inventory_product', 'product_id'),
        Index('idx_inventory_warehouse', 'warehouse_id'),
        Index('idx_inventory_batch', 'batch_number'),
        Index('idx_inventory_serial', 'serial_number'),
        Index('idx_inventory_expiry', 'expiry_date'),
        CheckConstraint('quantity_on_hand >= 0', name='chk_quantity_positive'),
        CheckConstraint('quantity_reserved >= 0 AND quantity_reserved <= quantity_on_hand',
                       name='chk_reserved_valid'),
    )

class StockMovement(Base):
    __tablename__ = 'stock_movements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False)
    bin_location_id = Column(Integer, ForeignKey('bin_locations.id', ondelete='SET NULL'))
    
    # Movement Details
    movement_type = Column(Enum(MovementType), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Reference to source transaction
    reference_type = Column(String(50))  # PO, SO, TRANSFER, ADJUSTMENT
    reference_id = Column(Integer)
    reference_number = Column(String(100))
    
    # Tracking
    batch_number = Column(String(100))
    serial_number = Column(String(100))
    
    # Costing
    unit_cost = Column(Float)
    total_value = Column(Float)
    
    # Details
    notes = Column(Text)
    
    # Audit
    created_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    movement_date = Column(DateTime, default=datetime.now(UTC))
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    __table_args__ = (
        Index('idx_movement_product', 'product_id'),
        Index('idx_movement_warehouse', 'warehouse_id'),
        Index('idx_movement_date', 'movement_date'),
        Index('idx_movement_type', 'movement_type'),
        Index('idx_movement_reference', 'reference_type', 'reference_id'),
    )

# 5. VENDOR MANAGEMENT MODULE
class Vendor(Base):
    __tablename__ = 'vendors'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    vendor_code = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    
    # Contact
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))
    
    # Address
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    
    # Business Terms
    payment_terms = Column(String(100))
    tax_id = Column(String(100))
    currency = Column(String(3), default='USD')
    credit_limit = Column(Float)
    current_balance = Column(Float, default=0.0)
    
    # Ratings
    rating = Column(Float)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    organization = relationship("Organization", back_populates="vendors")
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")
    
    __table_args__ = (
        Index('idx_vendor_code', 'vendor_code'),
        Index('idx_vendor_name', 'name'),
    )

# 6. PURCHASE ORDER MODULE
class PurchaseOrder(Base):
    __tablename__ = 'purchase_orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    po_number = Column(String(50), nullable=False, unique=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id', ondelete='RESTRICT'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False)
    
    # Dates
    order_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date)
    actual_delivery_date = Column(Date)
    
    # Status
    status = Column(Enum(OrderStatus), default=OrderStatus.DRAFT)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_method = Column(String(50))
    
    # Financial Details
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    discount_percentage = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    other_charges = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    
    currency = Column(String(3), default='USD')
    
    # Additional Info
    notes = Column(Text)
    terms_and_conditions = Column(Text)
    internal_notes = Column(Text)
    
    # Audit
    created_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    approved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    vendor = relationship("Vendor", back_populates="purchase_orders", lazy='joined')
    items = relationship("PurchaseOrderItem", back_populates="purchase_order", cascade="all, delete-orphan", lazy='selectin')
    goods_received_notes = relationship("GoodsReceivedNote", back_populates="purchase_order", lazy='selectin')
    
    __table_args__ = (
        Index('idx_po_number', 'po_number'),
        Index('idx_po_vendor', 'vendor_id'),
        Index('idx_po_status_date', 'status', 'order_date'),
    )

class PurchaseOrderItem(Base):
    __tablename__ = 'purchase_order_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id = Column(Integer, ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    line_number = Column(Integer, nullable=False)
    
    # Quantities
    quantity_ordered = Column(Integer, nullable=False)
    quantity_received = Column(Integer, default=0)
    
    # Pricing
    unit_price = Column(Float, nullable=False)
    tax_rate = Column(Float, default=0.0)
    discount_percentage = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    
    expected_date = Column(Date)
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    
    @hybrid_property
    def quantity_pending(self):
        return self.quantity_ordered - self.quantity_received
    
    @hybrid_property
    def line_total(self):
        return ((self.quantity_ordered * self.unit_price - self.discount_amount) * 
                (1 + self.tax_rate / 100))
    
    __table_args__ = (
        UniqueConstraint('purchase_order_id', 'line_number', name='unique_po_line'),
        Index('idx_po_item_po_id', 'purchase_order_id'),
        Index('idx_po_item_product_id', 'product_id'),
    )

class GoodsReceivedNote(Base):
    __tablename__ = 'goods_received_notes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    grn_number = Column(String(50), nullable=False, unique=True)
    purchase_order_id = Column(Integer, ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False)
    
    received_date = Column(Date, nullable=False)
    received_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    
    status = Column(String(20), default='PARTIAL')  # PARTIAL, COMPLETE
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    purchase_order = relationship("PurchaseOrder", back_populates="goods_received_notes")
    items = relationship("GRNItem", back_populates="grn", cascade="all, delete-orphan")

class GRNItem(Base):
    __tablename__ = 'grn_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    grn_id = Column(Integer, ForeignKey('goods_received_notes.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    po_item_id = Column(Integer, ForeignKey('purchase_order_items.id', ondelete='CASCADE'), nullable=False)
    
    quantity_received = Column(Integer, nullable=False)
    
    # Tracking
    batch_number = Column(String(100))
    serial_number = Column(String(100))
    manufacture_date = Column(Date)
    expiry_date = Column(Date)
    
    bin_location = Column(String(100))
    condition = Column(String(20), default='GOOD')  # GOOD, DAMAGED, EXPIRED
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    grn = relationship("GoodsReceivedNote", back_populates="items")

# 7. CUSTOMER MANAGEMENT MODULE
class Customer(Base):
    __tablename__ = 'customers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    customer_code = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    
    # Contact
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    
    # Addresses
    billing_address = Column(Text)
    shipping_address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    
    # Business Terms
    payment_terms = Column(String(100))
    tax_id = Column(String(100))
    credit_limit = Column(Float)
    outstanding_balance = Column(Float, default=0.0)
    
    # Customer Type
    customer_type = Column(String(50))  # retail, wholesale, distributor
    rating = Column(Float)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    organization = relationship("Organization", back_populates="customers")
    sales_orders = relationship("SalesOrder", back_populates="customer")


# 8. SALES ORDER MODULE

class SalesOrder(Base):
    __tablename__ = 'sales_orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    so_number = Column(String(50), nullable=False, unique=True)
    customer_id = Column(Integer, ForeignKey('customers.id', ondelete='RESTRICT'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False)
    
    # Dates
    order_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date)
    actual_delivery_date = Column(Date)
    
    # Status
    status = Column(Enum(SalesOrderStatus), default=SalesOrderStatus.DRAFT)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_method = Column(String(50))
    
    # Priority
    priority = Column(String(20), default='MEDIUM')  # LOW, MEDIUM, HIGH, URGENT
    
    # Shipping
    shipping_method = Column(String(100))
    tracking_number = Column(String(100))
    carrier = Column(String(100))
    
    # Financial Details
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    discount_percentage = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    
    currency = Column(String(3), default='USD')
    
    # Additional Info
    notes = Column(Text)
    customer_po_number = Column(String(100))
    internal_notes = Column(Text)
    
    # Sales Person
    sales_person_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    
    # Audit
    created_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    approved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    customer = relationship("Customer", back_populates="sales_orders")
    items = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")
    shipments = relationship("Shipment", back_populates="sales_order")
    
    __table_args__ = (
        Index('idx_so_number', 'so_number'),
        Index('idx_so_customer', 'customer_id'),
        Index('idx_so_status_date', 'status', 'order_date'),
        Index('idx_so_tracking', 'tracking_number'),
    )

class SalesOrderItem(Base):
    __tablename__ = 'sales_order_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sales_order_id = Column(Integer, ForeignKey('sales_orders.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    line_number = Column(Integer, nullable=False)
    
    # Quantities
    quantity_ordered = Column(Integer, nullable=False)
    quantity_shipped = Column(Integer, default=0)
    
    # Pricing
    unit_price = Column(Float, nullable=False)
    tax_rate = Column(Float, default=0.0)
    discount_percentage = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    sales_order = relationship("SalesOrder", back_populates="items")
    
    @hybrid_property
    def quantity_pending(self):
        return self.quantity_ordered - self.quantity_shipped
    
    @hybrid_property
    def line_total(self):
        return ((self.quantity_ordered * self.unit_price - self.discount_amount) * 
                (1 + self.tax_rate / 100))
    
    __table_args__ = (
        UniqueConstraint('sales_order_id', 'line_number', name='unique_so_line'),
        Index('idx_so_item_so_id', 'sales_order_id'),
        Index('idx_so_item_product_id', 'product_id'),
    )

class Shipment(Base):
    __tablename__ = 'shipments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_number = Column(String(50), nullable=False, unique=True)
    sales_order_id = Column(Integer, ForeignKey('sales_orders.id', ondelete='CASCADE'), nullable=False)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False)
    
    shipment_date = Column(Date, nullable=False)
    
    # Shipping Details
    carrier = Column(String(100))
    tracking_number = Column(String(100))
    shipping_cost = Column(Float, default=0.0)
    
    # Status
    status = Column(String(20), default='PACKED')  # PACKED, SHIPPED, IN_TRANSIT, DELIVERED, RETURNED
    
    # Dimensions & Weight
    total_weight = Column(Float)
    weight_unit = Column(String(10))  # kg, lbs
    
    notes = Column(Text)
    
    # Audit
    packed_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    shipped_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    sales_order = relationship("SalesOrder", back_populates="shipments")
    items = relationship("ShipmentItem", back_populates="shipment", cascade="all, delete-orphan")

class ShipmentItem(Base):
    __tablename__ = 'shipment_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(Integer, ForeignKey('shipments.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    so_item_id = Column(Integer, ForeignKey('sales_order_items.id', ondelete='CASCADE'), nullable=False)
    
    quantity_shipped = Column(Integer, nullable=False)
    
    # Tracking
    batch_number = Column(String(100))
    serial_number = Column(String(100))
    bin_location = Column(String(100))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    # Relationships
    shipment = relationship("Shipment", back_populates="items")

# 9. STOCK TRANSFER MODULE

class StockTransfer(Base):
    __tablename__ = 'stock_transfers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transfer_number = Column(String(50), nullable=False, unique=True)
    
    from_warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False)
    to_warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False)
    
    # Dates
    transfer_date = Column(Date, nullable=False)
    expected_date = Column(Date)
    actual_received_date = Column(Date)
    
    # Status
    status = Column(Enum(TransferStatus), default=TransferStatus.PENDING)
    
    # Shipping
    shipping_method = Column(String(100))
    tracking_number = Column(String(100))
    carrier = Column(String(100))
    
    notes = Column(Text)
    
    # Audit
    requested_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    approved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    approved_at = Column(DateTime)
    received_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    received_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    items = relationship("StockTransferItem", back_populates="stock_transfer", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint('from_warehouse_id != to_warehouse_id', name='chk_different_warehouses'),
        Index('idx_transfer_number', 'transfer_number'),
        Index('idx_transfer_from_warehouse', 'from_warehouse_id'),
        Index('idx_transfer_to_warehouse', 'to_warehouse_id'),
    )

class StockTransferItem(Base):
    __tablename__ = 'stock_transfer_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_transfer_id = Column(Integer, ForeignKey('stock_transfers.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    
    quantity_requested = Column(Integer, nullable=False)
    quantity_sent = Column(Integer, default=0)
    quantity_received = Column(Integer, default=0)
    
    # Tracking
    batch_number = Column(String(100))
    serial_number = Column(String(100))
    from_bin_location = Column(String(100))
    to_bin_location = Column(String(100))
    
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    stock_transfer = relationship("StockTransfer", back_populates="items")

# 10. STOCK ADJUSTMENT MODULE

class StockAdjustment(Base):
    __tablename__ = 'stock_adjustments'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    adjustment_number = Column(String(50), nullable=False, unique=True)
    warehouse_id = Column(Integer, ForeignKey('warehouses.id', ondelete='RESTRICT'), nullable=False)
    
    adjustment_date = Column(Date, nullable=False)
    reason = Column(Enum(AdjustmentReason), nullable=False)
    status = Column(String(20), default='DRAFT')  # DRAFT, PENDING_APPROVAL, APPROVED, REJECTED
    
    notes = Column(Text)
    
    # Audit
    created_by = Column(Integer, ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    approved_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    approved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    items = relationship("StockAdjustmentItem", back_populates="stock_adjustment", cascade="all, delete-orphan")

class StockAdjustmentItem(Base):
    __tablename__ = 'stock_adjustment_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_adjustment_id = Column(Integer, ForeignKey('stock_adjustments.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='RESTRICT'), nullable=False)
    
    quantity_before = Column(Integer, nullable=False)
    quantity_counted = Column(Integer, nullable=False)
    
    # Tracking
    batch_number = Column(String(100))
    serial_number = Column(String(100))
    bin_location = Column(String(100))
    
    # Costing
    unit_cost = Column(Float)
    
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.now(UTC))
    updated_at = Column(DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    stock_adjustment = relationship("StockAdjustment", back_populates="items")
    
    @hybrid_property
    def quantity_adjusted(self):
        return self.quantity_counted - self.quantity_before
    
    @hybrid_property
    def quantity_after(self):
        return self.quantity_counted
    
    @hybrid_property
    def total_value_change(self):
        if self.unit_cost:
            return (self.quantity_counted - self.quantity_before) * self.unit_cost
        return 0

# 11. AUDIT & LOGGING MODULE

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    action = Column(String(20), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, etc.
    
    # Entity Information
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer)
    
    # Change Tracking (stored as JSON strings)
    old_values = Column(Text)
    new_values = Column(Text)
    
    # Request Information
    ip_address = Column(String(50))
    user_agent = Column(Text)
    endpoint = Column(String(255))
    http_method = Column(String(10))
    
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    __table_args__ = (
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_entity', 'entity_type', 'entity_id'),
        Index('idx_audit_created', 'created_at'),
    )

class ActivityLog(Base):
    __tablename__ = 'activity_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    user_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'))
    activity_type = Column(String(100), nullable=False)
    description = Column(Text)
    meta_data = Column(Text)  # JSON string
    
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    __table_args__ = (
        Index('idx_activity_user', 'user_id'),
        Index('idx_activity_type', 'activity_type'),
    )

class NotificationLog(Base):
    __tablename__ = 'notification_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type = Column(String(50), nullable=False)  # email, sms, push, in_app
    
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    
    # Priority
    priority = Column(String(20), default='MEDIUM')  # LOW, MEDIUM, HIGH, URGENT
    
    # Additional Data
    meta_data = Column(Text)  # JSON string
    
    created_at = Column(DateTime, default=datetime.now(UTC))
    
    __table_args__ = (
        Index('idx_notification_user', 'user_id'),
        Index('idx_notification_read', 'is_read'),
        Index('idx_notification_priority', 'priority'),
    )

# EVENT LISTENERS (for automatic updates)

from sqlalchemy import event

@event.listens_for(InventoryStock, 'before_update')
def validate_inventory_stock(mapper, connection, target):
    """Validate inventory stock before update"""
    if target.quantity_reserved > target.quantity_on_hand:
        raise ValueError("Reserved quantity cannot exceed on-hand quantity")
    if target.quantity_on_hand < 0:
        raise ValueError("On-hand quantity cannot be negative")

__all__ = [
    'Base',
    'Organization', 'Role', 'User', 'UserSession',
    'Category', 'Product', 'ProductVariant', 'ProductImage',
    'Warehouse', 'WarehouseZone', 'BinLocation',
    'InventoryStock', 'StockMovement',
    'Vendor', 'PurchaseOrder', 'PurchaseOrderItem', 'GoodsReceivedNote', 'GRNItem',
    'Customer', 'SalesOrder', 'SalesOrderItem', 'Shipment', 'ShipmentItem',
    'StockTransfer', 'StockTransferItem',
    'StockAdjustment', 'StockAdjustmentItem',
    'AuditLog', 'ActivityLog', 'NotificationLog'
]


