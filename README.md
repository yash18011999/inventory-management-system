cat > README.md << 'EOF'

# Inventory Management System

A complete inventory management system built with FastAPI and SQLAlchemy.

## Features

- ✅ Multi-warehouse inventory tracking
- ✅ Purchase order management with GRN
- ✅ Sales order fulfillment with shipments
- ✅ Stock reservation (prevents over-selling)
- ✅ Stock transfers between warehouses
- ✅ Stock adjustments and cycle counts
- ✅ JWT authentication
- ✅ RESTful API with auto-generated docs

## Tech Stack

- **Backend**: FastAPI (async)
- **Database**: MySQL 8.0+
- **ORM**: SQLAlchemy 2.0 (async)
- **Authentication**: JWT with bcrypt
- **API Docs**: Swagger UI / ReDoc

## Quick Start

### Prerequisites

- Python 3.9+
- MySQL 8.0+
- pip

### Installation

1. Clone the repository
   \`\`\`bash
   git clone https://github.com/yash18011999/inventory-management-system.git
   cd inventory-management-system
   \`\`\`

2. Create virtual environment
   \`\`\`bash
   python -m venv venv
   source venv/bin/activate # On Windows: venv\Scripts\activate
   \`\`\`

3. Install dependencies
   \`\`\`bash
   pip install -r requirements.txt
   \`\`\`

4. Configure environment
   \`\`\`bash
   cp .env.example .env

# Edit .env with your database credentials

\`\`\`

5. Run the application
   \`\`\`bash
   uvicorn main:app --reload or uv run fastapi dev main.py
   \`\`\`

6. Access the API

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

\`\`\`
inventory-management-system/
├── main.py # FastAPI application
├── database.py # Database configuration
├── models.py # SQLAlchemy models
├── routers/ # API endpoints
├── services/ # Business logic
├── schemas/ # Pydantic schemas
├── core/ # Security & utilities
├── requirements.txt # Dependencies
└── .env.example # Environment template
\`\`\`

## API Endpoints

### Authentication

- POST /api/v1/auth/register
- POST /api/v1/auth/login
- GET /api/v1/auth/me

### Products

- GET /api/v1/products
- POST /api/v1/products
- GET /api/v1/products/{id}
- PUT /api/v1/products/{id}

### Inventory

- GET /api/v1/inventory/stock
- POST /api/v1/inventory/stock
- POST /api/v1/inventory/stock/adjust
- GET /api/v1/inventory/movements

### Purchase Orders

- POST /api/v1/purchase-orders
- POST /api/v1/purchase-orders/{id}/send
- POST /api/v1/purchase-orders/grn

### Sales Orders

- POST /api/v1/sales-orders
- POST /api/v1/sales-orders/{id}/confirm
- POST /api/v1/sales-orders/shipments

## License

MIT License - See LICENSE file

## Support

For questions and support:

- Create an issue on GitHub
- Email: chouhanyashvardhan89@gmail.com
  EOF
