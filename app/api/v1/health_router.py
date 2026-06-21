"""Health Check Router."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import structlog

from app.application.usecases.token_health_check_usecase import TokenHealthCheckUseCase

logger = structlog.get_logger()
router = APIRouter(prefix="/health", tags=["health"])


def get_token_health_check_usecase():
    """Get token health check use case dependency."""
    from app.main import container
    return container.get_token_health_check_usecase()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    logger.info("health_check_requested")
    
    return {
        "status": "UP",
        "service": "srv-token-manager",
        "version": "1.0.0"
    }


@router.get("/token")
async def token_health_check(
    health_check_use_case: TokenHealthCheckUseCase = Depends(get_token_health_check_usecase)
) -> Dict[str, Any]:
    """Token health check endpoint."""
    logger.info("token_health_check_requested")
    
    try:
        health = await health_check_use_case.execute()
        logger.info("token_health_check_success", health=health)
        return health
        
    except Exception as e:
        logger.error("token_health_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness check endpoint."""
    logger.info("readiness_check_requested")
    
    # TODO: Add actual readiness checks (Redis connection, etc.)
    return {
        "status": "READY",
        "service": "srv-token-manager"
    }


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness check endpoint."""
    logger.info("liveness_check_requested")
    
    return {
        "status": "ALIVE",
        "service": "srv-token-manager"
    }
