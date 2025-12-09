"""
BAFL Backend API - Main Application Entry Point
"""
import time
from contextlib import asynccontextmanager
import os
import sys

# Ensure `physical_assesment/src` is on sys.path so `from src...` imports work
# when the app is run from the repository root (e.g. `uvicorn main:app`).
ROOT_DIR = os.path.dirname(__file__)
SRC_PATH = os.path.join(ROOT_DIR, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from src.core.config import settings
from src.core.logging import api_logger, log_api_request, log_error
from src.api.v1.router import api_v1_router
from src.schemas.common import HealthResponse, ErrorResponse
from src.utils.db_init import setup_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown events."""
    # Startup
    api_logger.info(f"Starting {settings.APP_NAME}...")
    
    try:
        # Initialize database
        setup_database()
        api_logger.info("Application startup completed successfully")
    except Exception as e:
        api_logger.error(f"Failed to start application: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    api_logger.info(f"Shutting down {settings.APP_NAME}...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for BAFL with JWT authentication and role-based access control",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
    }
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# Request logging middleware
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    """Middleware to log all API requests with timing."""
    start_time = time.time()
    
    # Extract username from token if available
    username = ""
    try:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            from src.core.security import TokenHandler
            token = auth_header.replace("Bearer ", "")
            payload = TokenHandler.decode_token(token)
            username = payload.get("sub", "unknown")
    except:
        pass
    
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log request
        log_api_request(
            request.method,
            str(request.url.path),
            response.status_code,
            username
        )
        
        # Add custom headers
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-API-Version"] = settings.APP_VERSION
        
        return response
    
    except Exception as e:
        log_error(e, f"{request.method} {request.url.path}")
        raise


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            detail="Validation error",
            error_code="VALIDATION_ERROR"
        ).model_dump()
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    log_error(exc, f"{request.method} {request.url.path}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="Internal server error",
            error_code="INTERNAL_ERROR"
        ).model_dump()
    )


# Include API routers
app.include_router(api_v1_router, prefix="/api")


# Root endpoints
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Root"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT
    )


if __name__ == "__main__":
    import uvicorn
    
    api_logger.info(f"Starting {settings.APP_NAME} server...")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
