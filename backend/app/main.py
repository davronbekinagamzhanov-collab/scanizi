"""
ScanIZI — Main FastAPI Application
Интеллектуальная система анализа товаров и запасов
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import create_tables

# Import routers
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.products import router as products_router
from app.api.routes import (
    sales_router,
    capital_router,
    stores_router,
    warehouses_router,
    employees_router,
    scanner_router,
    data_router,
    recommendations_router,
    demo_router,
    ai_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (only in development)."""
    if settings.ENVIRONMENT != "production":
        await create_tables()
    yield


app = FastAPI(
    title="ScanIZI API",
    description="Интеллектуальная система анализа товаров и запасов",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
allowed_origins = list(dict.fromkeys([
    settings.FRONTEND_URL,
    "https://scanizi-frontend.onrender.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(products_router)
app.include_router(sales_router)
app.include_router(capital_router)
app.include_router(stores_router)
app.include_router(warehouses_router)
app.include_router(employees_router)
app.include_router(scanner_router)
app.include_router(data_router)
app.include_router(recommendations_router)
app.include_router(demo_router)
app.include_router(ai_router)


@app.get("/health")
async def health_check():
    """Public health check endpoint."""
    return {
        "status": "ok",
        "service": "ScanIZI API",
        "version": "1.0.0",
    }
