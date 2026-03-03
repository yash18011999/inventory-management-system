# services/product_service.py
"""
Business logic for product management
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models import Product, Category, InventoryStock
from schemas import ProductCreate, ProductUpdate
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload


class ProductService:
    @staticmethod
    async def create_product(db: AsyncSession, product: ProductCreate, user_id: int) -> Product:
        """Create a new product"""
        # Check if SKU already exists
        existing = await db.execute(select(Product).where(Product.sku == product.sku))
        existing = existing.scalars().first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with SKU '{product.sku}' already exists"
            )
        
        db_product = Product(
            **product.model_dump(),
            created_by=user_id
        )
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product, attribute_names=["category", "creator"])
        return db_product
    
    @staticmethod
    async def get_products(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        is_active: Optional[bool] = None
    ) -> List[Product]:
        """Get list of products with filters"""
        query = select(Product).options(
            joinedload(Product.category),
            joinedload(Product.creator)
        )
        
        if search:
            result = query.where(
                or_(
                    Product.name.ilike(f"%{search}%"),
                    Product.sku.ilike(f"%{search}%"),
                    Product.barcode.ilike(f"%{search}%")
                )
            )
        
        if category_id is not None:
            query = query.where(Product.category_id == category_id)
        
        if is_active is not None:
            query = query.where(Product.is_active == is_active)
        
        result = query.order_by(Product.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(result)
        return result.scalars().unique().all()
    
    
    @staticmethod
    async def get_product(db: AsyncSession, product_id: int) -> Product:
        """Get single product by ID"""
        query = select(Product).options(
            joinedload(Product.category),
            joinedload(Product.creator),
            joinedload(Product.inventory_stock)  # Also load stock levels
        ).where(Product.id == product_id)

        result = await db.execute(query)
        product = result.scalars().unique().first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
        return product
    
    @staticmethod
    async def get_product_by_sku(db: AsyncSession, sku: str) -> Product:
        """Get product by SKU"""
        stmt = select(Product).options(
            joinedload(Product.category)
        ).where(Product.sku == sku)
        
        result = await db.execute(stmt)
        product = result.scalars().unique().first()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with SKU '{sku}' not found"
            )
        return product
    
    @staticmethod
    async def update_product(
        db: AsyncSession,
        product_id: int,
        product_update: ProductUpdate
    ) -> Product:
        """Update product"""
        product = await ProductService.get_product(db, product_id)
        
        update_data = product_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        
        await db.commit()
        await db.refresh(product, attribute_names=["category", "creator", "inventory_stock", "variants", "images"])
        return product
    
    @staticmethod
    async def delete_product(db: AsyncSession, product_id: int) -> bool:
        """Soft delete product (set is_active to False)"""
        product = await ProductService.get_product(db, product_id)
        product.is_active = False
        await db.commit()
        return True
    
    @staticmethod
    async def get_product_stock(db: AsyncSession, product_id: int) -> List[InventoryStock]:
        """Get stock levels for a product across all warehouses"""
        result = stmt = select(InventoryStock).options(
            joinedload(InventoryStock.warehouse)
        ).where(InventoryStock.product_id == product_id)

        result = await db.execute(stmt)
        return result.scalars().unique().all()