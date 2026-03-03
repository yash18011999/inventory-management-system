from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import User, Customer
from schemas import CustomerCreate, CustomerUpdate, CustomerResponse
from core.security import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


router = APIRouter()


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer: CustomerCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Create a new customer"""
    # Check if customer code exists
    existing = await db.execute(
        select(Customer).where(Customer.customer_code == customer.customer_code)
    )
    existing = existing.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer with code '{customer.customer_code}' already exists"
        )
    
    db_customer = Customer(**customer.dict())
    db.add(db_customer)
    await db.commit()
    await db.refresh(db_customer)
    return db_customer


@router.get("/", response_model=List[CustomerResponse])
async def list_customers(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """Get list of customers"""
    query = select(Customer)
    
    if search:
        from sqlalchemy import or_
        query = await db.execute(
            query.filter(
                or_(
                    Customer.name.ilike(f"%{search}%"),
                    Customer.customer_code.ilike(f"%{search}%"),
                    Customer.email.ilike(f"%{search}%")
                )
        ))
    
    if is_active is not None:
        query = query.where(Customer.is_active == is_active)
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Get a single customer by ID"""
    customer = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Update a customer"""
    customer = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
    
    update_data = customer_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    await db.commit()
    await db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(get_current_user)
):
    """Deactivate a customer"""
    customer = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    customer = customer.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {customer_id} not found"
        )
    
    customer.is_active = False
    await db.commit()
    return None