"""Metrics Router."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/")
async def get_metrics() -> Response:
    """Prometheus metrics endpoint."""
    logger.info("metrics_requested")
    
    try:
        metrics_data = generate_latest()
        logger.info("metrics_success")
        
        return Response(
            content=metrics_data,
            media_type=CONTENT_TYPE_LATEST
        )
        
    except Exception as e:
        logger.error("metrics_failed", error=str(e))
        return Response(
            content=f"Error generating metrics: {str(e)}",
            status_code=500
        )
