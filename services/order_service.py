# services/order_service.py
"""
Business logic for purchase orders and sales orders
"""

from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import UTC, datetime, date
from models import (
    PurchaseOrder, PurchaseOrderItem, GoodsReceivedNote, GRNItem,
    SalesOrder, SalesOrderItem, Shipment, ShipmentItem,
    Product, InventoryStock, StockMovement, SalesOrderStatus
)
from schemas.orders import (
    PurchaseOrderCreate, GRNCreate,
    SalesOrderCreate, ShipmentCreate, PurchaseOrderResponse
)
from services.inventory_service import InventoryService
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload



class PurchaseOrderService:
    @staticmethod
    async def generate_po_number(db: AsyncSession) -> str:
        """Generate next PO number"""
        last_po = await db.execute(select(PurchaseOrder).order_by(PurchaseOrder.id.desc()).limit(1))
        last_po = last_po.scalars().first()
        
        if last_po and last_po.po_number:
            # Extract number and increment
            try:
                last_num = int(last_po.po_number.split('-')[-1])
                new_num = last_num + 1
            except:
                new_num = 1
        else:
            new_num = 1
        
        return f"PO-{date.today().strftime('%Y')}-{new_num:05d}"
    
    @staticmethod
    async def create_purchase_order(
        db: AsyncSession,
        po_data: PurchaseOrderCreate,
        user_id: int
    ) -> PurchaseOrder:
        """Create a new purchase order"""
        # Generate PO number
        po_number = await PurchaseOrderService.generate_po_number(db)
        
        # Calculate totals
        subtotal = sum(
            item.quantity_ordered * item.unit_price - item.discount_amount
            for item in po_data.items
        )
        
        tax_amount = sum(
            (item.quantity_ordered * item.unit_price - item.discount_amount) * (item.tax_rate / 100)
            for item in po_data.items
        )
        
        total_amount = subtotal + tax_amount
        
        # Create PO
        po = PurchaseOrder(
            po_number=po_number,
            vendor_id=po_data.vendor_id,
            warehouse_id=po_data.warehouse_id,
            order_date=po_data.order_date,
            expected_delivery_date=po_data.expected_delivery_date,
            status="DRAFT",
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            notes=po_data.notes,
            terms_and_conditions=po_data.terms_and_conditions,
            created_by=user_id
        )
        
        db.add(po)
        await db.flush()
        
        # Add items
        for item_data in po_data.items:
            item = PurchaseOrderItem(
                purchase_order_id=po.id,
                **item_data.model_dump()
            )
            db.add(item)
        
        await db.commit()
        await db.refresh(po)
        # Re-query with eager loads to ensure relationships are loaded before returning
        res = await db.execute(
            select(PurchaseOrder)
            .options(joinedload(PurchaseOrder.vendor), selectinload(PurchaseOrder.items))
            .where(PurchaseOrder.id == po.id)
        )
        po = res.scalars().first()
        return po
    
    @staticmethod
    async def get_purchase_orders(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: str = None
    ) -> List[PurchaseOrder]:
        """Get list of purchase orders"""
        query = select(PurchaseOrder).options(
            joinedload(PurchaseOrder.vendor),
            selectinload(PurchaseOrder.items))
        
        if status:
            query = query.where(PurchaseOrder.status == status)
        
        query = query.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_purchase_order(db: AsyncSession, po_id: int) -> PurchaseOrder:
        """Get single purchase order"""
        result = await db.execute(
            select(PurchaseOrder).options(joinedload(PurchaseOrder.vendor), selectinload(PurchaseOrder.items)).where(PurchaseOrder.id == po_id)
        )
        po = result.scalars().first()
        if not po:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase order {po_id} not found"
            )
        return po
    
    @staticmethod
    async def update_po_status(
        db: AsyncSession,
        po_id: int,
        new_status: str,
        user_id: int
    ) -> PurchaseOrder:
        """Update PO status"""
        po = await PurchaseOrderService.get_purchase_order(db, po_id)
        
        if new_status == "SENT" and po.status == "DRAFT":
            po.status = "SENT"
            po.approved_by = user_id
            po.approved_at = datetime.now(UTC)
        else:
            po.status = new_status
        
        await db.commit()
        await db.refresh(po)
        return po
    
    @staticmethod
    async def receive_goods(
        db: AsyncSession,
        grn_data: GRNCreate,
        user_id: int
    ) -> GoodsReceivedNote:
        """Create GRN and update inventory"""
        # Get PO
        po = await PurchaseOrderService.get_purchase_order(db, grn_data.purchase_order_id)
        
        # Generate GRN number
        last_grn = await db.execute(select(GoodsReceivedNote).options(selectinload(GoodsReceivedNote.purchase_order)).order_by(GoodsReceivedNote.id.desc()).limit(1))
        last_grn = last_grn.scalars().first()
        grn_num = 1 if not last_grn else int(last_grn.grn_number.split('-')[-1]) + 1
        grn_number = f"GRN-{date.today().strftime('%Y')}-{grn_num:05d}"
        
        # Create GRN
        grn = GoodsReceivedNote(
            grn_number=grn_number,
            purchase_order_id=grn_data.purchase_order_id,
            warehouse_id=grn_data.warehouse_id,
            received_date=grn_data.received_date,
            received_by=user_id,
            status="COMPLETE",
            notes=grn_data.notes
        )
        db.add(grn)
        await db.flush()
        
        # Process items
        for item_data in grn_data.items:
            # Create GRN item
            grn_item = GRNItem(
                grn_id=grn.id,
                **item_data.model_dump()
            )
            db.add(grn_item)
            
            # Update PO item
            po_item = await db.execute(select(PurchaseOrderItem).where(PurchaseOrderItem.id == item_data.po_item_id))
            po_item = po_item.scalars().first()
            if po_item:
                po_item.quantity_received += item_data.quantity_received
            
            # Update inventory
            stock = await db.execute(select(InventoryStock).where(
                and_(
                    InventoryStock.product_id == item_data.product_id,
                    InventoryStock.warehouse_id == grn_data.warehouse_id,
                    InventoryStock.batch_number == item_data.batch_number if item_data.batch_number else True
                )
            ))
            stock = stock.scalars().first()
            
            if stock:
                stock.quantity_on_hand += item_data.quantity_received
            else:
                stock = InventoryStock(
                    product_id=item_data.product_id,
                    warehouse_id=grn_data.warehouse_id,
                    quantity_on_hand=item_data.quantity_received,
                    batch_number=item_data.batch_number,
                    serial_number=item_data.serial_number,
                    manufacture_date=item_data.manufacture_date,
                    expiry_date=item_data.expiry_date,
                    unit_cost=po_item.unit_price if po_item else None
                )
                db.add(stock)
            
            # Create stock movement
            movement = StockMovement(
                product_id=item_data.product_id,
                warehouse_id=grn_data.warehouse_id,
                movement_type="IN",
                quantity=item_data.quantity_received,
                reference_type="PO",
                reference_id=po.id,
                reference_number=po.po_number,
                batch_number=item_data.batch_number,
                serial_number=item_data.serial_number,
                unit_cost=po_item.unit_price if po_item else None,
                created_by=user_id
            )
            db.add(movement)
        
        # Update PO status
        all_received = all(
            item.quantity_received >= item.quantity_ordered
            for item in po.items
        )
        
        if all_received:
            po.status = "RECEIVED"
            po.actual_delivery_date = grn_data.received_date
        else:
            po.status = "PARTIAL"
        
        await db.commit()
        await db.refresh(grn)
        # Re-query GRN with its items and purchase order (and nested PO relationships) eagerly loaded
        res = await db.execute(
            select(GoodsReceivedNote)
            .options(
                selectinload(GoodsReceivedNote.items),
                joinedload(GoodsReceivedNote.purchase_order).joinedload(PurchaseOrder.vendor),
                joinedload(GoodsReceivedNote.purchase_order).selectinload(PurchaseOrder.items),
            )
            .where(GoodsReceivedNote.id == grn.id)
        )
        grn = res.scalars().first()
        return grn


class SalesOrderService:
    @staticmethod
    async def generate_so_number(db: AsyncSession) -> str:
        """Generate next SO number"""
        last_so = await db.execute(select(SalesOrder).order_by(
            SalesOrder.id.desc()
        ))
        last_so = last_so.scalars().first()
        
        if last_so and last_so.so_number:
            try:
                last_num = int(last_so.so_number.split('-')[-1])
                new_num = last_num + 1
            except:
                new_num = 1
        else:
            new_num = 1
        
        return f"SO-{date.today().strftime('%Y')}-{new_num:05d}"
    
    @staticmethod
    async def create_sales_order(
        db: AsyncSession,
        so_data: SalesOrderCreate,
        user_id: int
    ) -> SalesOrder:
        """Create a new sales order"""
        # Generate SO number
        so_number = await SalesOrderService.generate_so_number(db)
        
        # Calculate totals
        subtotal = sum(
            item.quantity_ordered * item.unit_price - item.discount_amount
            for item in so_data.items
        )
        
        tax_amount = sum(
            (item.quantity_ordered * item.unit_price - item.discount_amount) * (item.tax_rate / 100)
            for item in so_data.items
        )
        
        total_amount = subtotal + tax_amount
        
        # Create SO
        so = SalesOrder(
            so_number=so_number,
            customer_id=so_data.customer_id,
            warehouse_id=so_data.warehouse_id,
            order_date=so_data.order_date,
            expected_delivery_date=so_data.expected_delivery_date,
            priority=so_data.priority,
            shipping_method=so_data.shipping_method,
            customer_po_number=so_data.customer_po_number,
            status="DRAFT",
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            notes=so_data.notes,
            created_by=user_id
        )
        
        db.add(so)
        await db.flush()
        
        # Add items
        for item_data in so_data.items:
            item = SalesOrderItem(
                sales_order_id=so.id,
                **item_data.model_dump()
            )
            db.add(item)
        
        await db.commit()
        await db.refresh(so)

        res = await db.execute(
            select(SalesOrder)
            .options(selectinload(SalesOrder.items))
            .where(SalesOrder.id == so.id)
        )
        return res.scalars().first()
    
    @staticmethod
    async def confirm_sales_order(db: AsyncSession, so_id: int, user_id: int) -> SalesOrder:
        """Confirm SO and reserve stock"""
        res = await db.execute(select(SalesOrder).options(selectinload(SalesOrder.items), joinedload(SalesOrder.customer)).where(SalesOrder.id == so_id))
        so = res.scalars().unique().first()
        if not so:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sales order {so_id} not found"
            )
        
        if so.status != SalesOrderStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order is already {so.status}"
            )
        
        # Reserve stock for each item
        try:
            print(f"Reserving stock for {so.so_number}...")
            for item in so.items:
                print(f"Reserving {item.quantity_ordered} units of product {item.product_id}...")
                await InventoryService.reserve_stock(
                    db=db,
                    product_id=item.product_id,
                    warehouse_id=so.warehouse_id,
                    quantity=item.quantity_ordered
                )
                print(f"Reserving stock for SO {so.so_number}...")

        except HTTPException as e:
            await db.rollback()
            print(f"Failed to confirm SO {so.so_number}: {e.detail}")
            raise e
        
        so.status = SalesOrderStatus.CONFIRMED
        so.approved_by = user_id
        so.approved_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(so, attribute_names=["customer", "items", "shipments"])

        res = await db.execute(
            select(SalesOrder)
            .options(selectinload(SalesOrder.items), joinedload(SalesOrder.customer), selectinload(SalesOrder.shipments))
            .where(SalesOrder.id == so.id)
        )
        return res.scalars().first()
    
    @staticmethod
    async def create_shipment(
        db: AsyncSession,
        shipment_data: ShipmentCreate,
        user_id: int
    ) -> Shipment:
        """Create shipment and deduct stock"""
        so = await db.execute(select(SalesOrder).options(selectinload(SalesOrder.items)).where(SalesOrder.id == shipment_data.sales_order_id))
        so = so.scalars().unique().first()
        
        if not so:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales order not found"
            )
        
        # Generate shipment number
        last_ship = await db.execute(select(Shipment).order_by(Shipment.id.desc()))
        last_ship = last_ship.scalars().first()
        ship_num = 1 if not last_ship else int(last_ship.shipment_number.split('-')[-1]) + 1
        shipment_number = f"SHIP-{date.today().strftime('%Y')}-{ship_num:05d}"
        
        # Create shipment
        shipment = Shipment(
            shipment_number=shipment_number,
            sales_order_id=shipment_data.sales_order_id,
            warehouse_id=shipment_data.warehouse_id,
            shipment_date=shipment_data.shipment_date,
            carrier=shipment_data.carrier,
            tracking_number=shipment_data.tracking_number,
            shipping_cost=shipment_data.shipping_cost,
            status="SHIPPED",
            packed_by=user_id
        )
        db.add(shipment)
        await db.flush()
        
        # Process items
        for item_data in shipment_data.items:
            shipment_item = ShipmentItem(
                shipment_id=shipment.id,
                **item_data.model_dump()
            )
            db.add(shipment_item)
            
            # Update SO item            
            so_item = await db.execute(select(SalesOrderItem).where(SalesOrderItem.id == item_data.so_item_id))
            so_item = so_item.scalars().first()
            if so_item:
                so_item.quantity_shipped += item_data.quantity_shipped
            
            # Deduct from inventory
            await InventoryService.deduct_stock(
                db=db,
                product_id=item_data.product_id,
                warehouse_id=shipment_data.warehouse_id,
                quantity=item_data.quantity_shipped,
                reference_type="SO",
                reference_id=so.id,
                reference_number=so.so_number,
                user_id=user_id,
                batch_number=item_data.batch_number
            )
        
        # Update SO status
        all_shipped = all(
            item.quantity_shipped >= item.quantity_ordered
            for item in so.items
        )
        
        if all_shipped:
            so.status = SalesOrderStatus.SHIPPED
            so.tracking_number = shipment_data.tracking_number
        else:
            so.status = SalesOrderStatus.PACKED
        
        await db.commit()
        await db.refresh(shipment)
        res = await db.execute(
            select(Shipment)
            .options(
                selectinload(Shipment.items)            )
            .where(Shipment.id == shipment.id)
        )
        shipment = res.scalars().unique().first()
        return shipment