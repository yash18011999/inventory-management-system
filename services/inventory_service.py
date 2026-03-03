# services/inventory_service.py
"""
Business logic for inventory management
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from models import InventoryStock, StockMovement, Product, Warehouse
from schemas import InventoryStockCreate, InventoryStockUpdate, StockMovementCreate
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload



class InventoryService:
    @staticmethod
    async def get_stock(
        db: AsyncSession,
        product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        low_stock_only: bool = False
    ) -> List[InventoryStock]:
        """Get inventory stock with filters"""
        query = select(InventoryStock).options(joinedload(InventoryStock.product), joinedload(InventoryStock.warehouse))
        
        if product_id:
            query = query.where(InventoryStock.product_id == product_id)
        
        if warehouse_id:
            query = query.where(InventoryStock.warehouse_id == warehouse_id)
        
        result = await db.execute(query)
        results = result.scalars().unique().all() 
        
        if low_stock_only:
            # Filter for low stock items
            filtered_results = []
            for stock in results:
                for stock in results:
                    if stock.product and stock.quantity_available <= stock.product.reorder_level:
                        filtered_results.append(stock)
            return filtered_results
        
        return results
    
    @staticmethod
    async def get_stock_by_id(db: AsyncSession, stock_id: int) -> InventoryStock:
        """Get specific stock record"""
        stock = select(InventoryStock).options(
            joinedload(InventoryStock.product),
            joinedload(InventoryStock.warehouse)
            ).where(InventoryStock.id == stock_id)
        
        stock = await db.execute(stock)
        stock = stock.scalars().unique().first()
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock record {stock_id} not found"
            )
        return stock
    
    @staticmethod
    async def create_or_update_stock(
        db: AsyncSession,
        stock_data: InventoryStockCreate,
        user_id: int
    ) -> InventoryStock:
        """Create or update inventory stock"""
        # Check if stock record exists
        existing_stock = select(InventoryStock).where(
            and_(
                InventoryStock.product_id == stock_data.product_id,
                InventoryStock.warehouse_id == stock_data.warehouse_id,
                InventoryStock.batch_number == stock_data.batch_number
            )
        )
        
        result = await db.execute(existing_stock)
        existing_stock = result.scalars().first()
        
        if existing_stock:
            # Update existing
            existing_stock.quantity_on_hand += stock_data.quantity_on_hand
            await db.commit()
            await db.refresh(existing_stock, attribute_names=["product", "warehouse"])
            stock = existing_stock
        else:
            # Create new
            stock = InventoryStock(**stock_data.dict())
            db.add(stock)
            await db.commit()
            await db.refresh(stock)
        
        # Create stock movement record
        movement = StockMovement(
            product_id=stock.product_id,
            warehouse_id=stock.warehouse_id,
            movement_type="IN",
            quantity=stock_data.quantity_on_hand,
            reference_type="MANUAL",
            batch_number=stock_data.batch_number,
            serial_number=stock_data.serial_number,
            unit_cost=stock_data.unit_cost,
            created_by=user_id
        )
        db.add(movement)
        await db.commit()
        
        return stock
    
    @staticmethod
    async def adjust_stock(
        db: AsyncSession,
        product_id: int,
        warehouse_id: int,
        quantity_change: int,
        reason: str,
        user_id: int,
        batch_number: Optional[str] = None
    ) -> InventoryStock:
        """Adjust inventory stock levels"""
        # Lock the row for update
        stmt = select(InventoryStock).where(
            and_(
                InventoryStock.product_id == product_id,
                InventoryStock.warehouse_id == warehouse_id,
                InventoryStock.batch_number == batch_number if batch_number else True
            )
        ).with_for_update()

        stock = await db.execute(stmt)
        stock = stock.scalars().first()
        
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock not found for product {product_id} in warehouse {warehouse_id}"
            )
        
        old_quantity = stock.quantity_on_hand
        new_quantity = old_quantity + quantity_change
        
        if new_quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {stock.quantity_on_hand}, Required: {abs(quantity_change)}"
            )
        
        stock.quantity_on_hand = new_quantity
        
        # Create stock movement
        movement = StockMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type="ADJUST",
            quantity=quantity_change,
            reference_type="ADJUSTMENT",
            notes=reason,
            batch_number=batch_number,
            created_by=user_id
        )
        db.add(movement)
        
        await db.commit()
        await db.refresh(stock)
        return stock
    
    @staticmethod
    async def reserve_stock(
        db: AsyncSession,
        product_id: int,
        warehouse_id: int,
        quantity: int,
        batch_number: Optional[str] = None
    ) -> InventoryStock:
        """Reserve stock for an order"""
        print(f"Reserving {quantity} units of product {product_id} in warehouse {warehouse_id}...")
        # Lock the row
        stmt = await db.execute(select(InventoryStock).where(
            and_(
                InventoryStock.product_id == product_id,
                InventoryStock.warehouse_id == warehouse_id,
            )
        ).with_for_update())

        # stock = await db.execute(stmt)
        stock = stmt.scalars().first()
        
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock not found for product {product_id}"
            )
        
        if stock.quantity_available < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {stock.quantity_available}, Required: {quantity}"
            )
        
        stock.quantity_reserved += quantity
        await db.commit()
        await db.refresh(stock)
        return stock
    
    @staticmethod
    async def release_reservation(
        db: AsyncSession,
        product_id: int,
        warehouse_id: int,
        quantity: int,
        batch_number: Optional[str] = None
    ) -> InventoryStock:
        """Release reserved stock"""
        stmt = select(InventoryStock).where(
            and_(
                InventoryStock.product_id == product_id,
                InventoryStock.warehouse_id == warehouse_id,
                InventoryStock.batch_number == batch_number if batch_number else True
            )
        )

        stock = await db.execute(stmt)
        stock = stock.scalars().first()
        
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock not found"
            )
        
        stock.quantity_reserved = max(0, stock.quantity_reserved - quantity)
        await db.commit()
        await db.refresh(stock)
        return stock
    
    @staticmethod
    async def deduct_stock(
        db: AsyncSession,
        product_id: int,
        warehouse_id: int,
        quantity: int,
        reference_type: str,
        reference_id: int,
        reference_number: str,
        user_id: int,
        batch_number: Optional[str] = None,
        also_release_reservation: bool = True
    ) -> InventoryStock:
        """Deduct stock (e.g., when shipping an order)"""
        stmt = await db.execute(select(InventoryStock).where(
            and_(
                InventoryStock.product_id == product_id,
                InventoryStock.warehouse_id == warehouse_id,
                InventoryStock.batch_number == batch_number if batch_number else True
            )
        ).with_for_update())

        stock = stmt.scalars().first()
        
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock not found"
            )
        
        if stock.quantity_on_hand < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {stock.quantity_on_hand}, Required: {quantity}"
            )
        
        stock.quantity_on_hand -= quantity
        
        if also_release_reservation:
            stock.quantity_reserved = max(0, stock.quantity_reserved - quantity)
        
        # Create stock movement
        movement = StockMovement(
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type="OUT",
            quantity=quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            reference_number=reference_number,
            batch_number=batch_number,
            created_by=user_id
        )
        db.add(movement)
        
        await db.commit()
        await db.refresh(stock)
        return stock
    
    @staticmethod
    async def get_stock_movements(
        db: AsyncSession,
        product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        limit: int = 100
    ) -> List[StockMovement]:
        """Get stock movement history"""
        stmt = select(StockMovement)
        
        if product_id:
            stmt = stmt.where(StockMovement.product_id == product_id)
        
        if warehouse_id:
            stmt = stmt.where(StockMovement.warehouse_id == warehouse_id)
        
        if movement_type:
            stmt = stmt.where(StockMovement.movement_type == movement_type)
        
        return (await db.execute(stmt.order_by(StockMovement.movement_date.desc()).limit(limit))).scalars().unique().all()
    
    @staticmethod
    async def get_low_stock_report(db: AsyncSession, warehouse_id: Optional[int] = None):
        """Get products with low stock"""
        stmt = select(
            Product.id.label('product_id'),
            Product.sku,
            Product.name.label('product_name'),
            Product.reorder_level,
            Warehouse.id.label('warehouse_id'),
            Warehouse.name.label('warehouse_name'),
            func.sum(
                InventoryStock.quantity_on_hand - InventoryStock.quantity_reserved
            ).label('quantity_available')
        ).join(
            InventoryStock, Product.id == InventoryStock.product_id
        ).join(
            Warehouse, InventoryStock.warehouse_id == Warehouse.id
        ).where(
            Product.is_active == True
        ).group_by(
            Product.id, Warehouse.id
        ).having(
            func.sum(InventoryStock.quantity_on_hand - InventoryStock.quantity_reserved) <= Product.reorder_level
        )
        
        if warehouse_id:
            stmt = stmt.where(Warehouse.id == warehouse_id)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        # Filter for low stock
        return [
            {
                "product_id": row.product_id,
                "sku": row.sku,
                "product_name": row.product_name,
                "warehouse_id": row.warehouse_id,
                "warehouse_name": row.warehouse_name,
                "quantity_available": row.quantity_available,
                "reorder_level": row.reorder_level
            }
            for row in rows
        ]