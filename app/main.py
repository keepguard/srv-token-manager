"""FastAPI Application Main Module."""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.infrastructure.config.settings import load_settings
from app.infrastructure.config.container import Container
from app.infrastructure.monitoring.logger import configure_logging, get_logger
from app.infrastructure.monitoring.metrics import update_app_info
from app.api.v1 import health_router, token_router, metrics_router

# Load settings
settings = load_settings()

# Configure logging
configure_logging(level=settings.log.level, format_type=settings.log.format)
logger = get_logger(__name__)

# Update app info metrics
update_app_info(
    version=settings.app_version,
    environment=settings.env,
    python_version="3.11"
)

# Global container instance
container: Container = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global container
    
    logger.info("application_starting", version=settings.app_version, env=settings.env)
    
    try:
        # Initialize container
        container = Container(settings)
        
        # Startup dependencies
        await container.startup()
        
        logger.info("application_startup_complete")
        
        # Yield control to application
        yield
        
    except Exception as e:
        logger.error("application_startup_failed", error=str(e))
        raise
    finally:
        # Shutdown dependencies
        if container:
            await container.shutdown()
        
        logger.info("application_shutdown_complete")


# Create FastAPI app
app = FastAPI(
    title="Token Manager Service",
    description="OAuth2 Token Manager for Gmail with Redis cache and proactive refresh",
    version=settings.app_version,
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

# Dependency injection functions
def get_container() -> Container:
    """Get container instance."""
    return container

def get_get_token_usecase():
    """Get token use case dependency."""
    return container.get_get_token_usecase()

def get_refresh_token_usecase():
    """Get refresh token use case dependency."""
    return container.get_refresh_token_usecase()

def get_token_status_usecase():
    """Get token status use case dependency."""
    return container.get_token_status_usecase()

def get_token_health_check_usecase():
    """Get token health check use case dependency."""
    return container.get_token_health_check_usecase()

# Include routers with dependencies
app.include_router(health_router.router)
app.include_router(token_router.router)
app.include_router(metrics_router.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "srv-token-manager",
        "version": settings.app_version,
        "status": "running",
        "environment": settings.env
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.env == "local",
        log_level=settings.log.level
    )
