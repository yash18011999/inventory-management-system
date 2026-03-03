from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from contextlib import asynccontextmanager
import time
import os

from database import Base, engine, get_db

from routers import (
    auth,
    products,
    categories,
    warehouses,
    inventory,
    purchase_orders,
    sales_orders,
    vendors,
    customers,
    stock_transfers,
    stock_adjustments,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Inventory Management System API...")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

    # Shutdown
    print("Shutting down Inventory Management System API...")
    await engine.dispose()
    


    
app = FastAPI(
    title="Inventory Management System",
    description="""
    ## Inventory Management System API
    
    ### Features
    * Product catalog management
    * Multi warehouse inventory tracking
    * Purchase order processing with GRN
    * Sales order fulfillment with shipments
    * Stock transfers between warehouses
    * Stock adjustments and cycle counts
    * Real-time inventory reporting
    * JWT authentication
    * Compelete audit trail
    
    ### Workflow
    
    **Purchase Flow:**
    1. Create Purchase Order (DRAFT)
    2. Send to Vendor (SENT)
    3. Receive Goods with GRN (PARTIAL/RECEIVED)
    
    **Sales Flow:**
    1. Create Sales Order (DRAFT)
    2. Confirm Order - reserves stock (CONFIRMED)
    3. Create Shipment - deducts stock (SHIPPED)
    4. Mark as Delivered (DELIVERED)
    
    **Transfer Flow:**
    1. Create Transfer Request (PENDING)
    2. Approve Transfer (APPROVED)
    3. Send Stock (IN_TRANSIT)
    4. Receive at Destination (COMPLETED)
    
    ### Authentication
    All endpoints (except /auth/login and /auth/register) require Bearer token authentication.
    
    Get token: `POST /api/v1/auth/login`
    Use token: `Authorization: Bearerr <your_token>`
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],  # Allow all origins for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle vailidation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body
        }
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "error": str(exc)
        }
    )

@app.get("/", tags=["Root"])
def read_root():
    """API root endpoint"""
    return {
        "message": "Inventory Management System API",
        "docs": "/docs",
        "redoc": "/redoc",
        "status": "operational"
    }

API_V1 = "/api/v1"

# Routrers
app.include_router(auth.router, prefix=f"{API_V1}/auth", tags=["Authentication"])
app.include_router(products.router, prefix=f"{API_V1}/products", tags=["Products"])
app.include_router(categories.router, prefix=f"{API_V1}/categories", tags=["Categories"])
app.include_router(warehouses.router, prefix=f"{API_V1}/warehouses", tags=["Warehouses"])
app.include_router(inventory.router, prefix=f"{API_V1}/inventory", tags=["Inventory"])
app.include_router(vendors.router, prefix=f"{API_V1}/vendors", tags=["Vendors"])
app.include_router(customers.router, prefix=f"{API_V1}/customers", tags=["Customers"])
app.include_router(purchase_orders.router, prefix=f"{API_V1}/purchase-orders", tags=["Purchase Orders"])
app.include_router(sales_orders.router, prefix=f"{API_V1}/sales-orders", tags=["Sales Orders"])
app.include_router(stock_transfers.router, prefix=f"{API_V1}/stock-transfers", tags=["Stock Transfers"])
app.include_router(stock_adjustments.router, prefix=f"{API_V1}/stock-adjustments", tags=["Stock Adjustments"])


