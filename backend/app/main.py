"""
Main FastAPI application for County Health Explorer.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .database import init_database, get_db
from .routes.api import router as api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting County Health Explorer API")
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down County Health Explorer API")
    db = get_db()
    db.close()


# Create FastAPI application
app = FastAPI(
    title="County Health Explorer API",
    description="Spatial data science API for exploring U.S. county-level health data",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for consistent error responses."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "status": 500,
            "details": "An unexpected error occurred"
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        db = get_db()
        with db.get_cursor() as conn:
            # Test database connection
            result = conn.execute("SELECT COUNT(*) FROM county_health").fetchone()
            health_records = result[0] if result else 0
            
            result = conn.execute("SELECT COUNT(*) FROM county_spatial").fetchone()
            spatial_records = result[0] if result else 0
            
        return {
            "status": "healthy",
            "database": "connected",
            "health_records": health_records,
            "spatial_records": spatial_records
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "County Health Explorer API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "api": "/api"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 