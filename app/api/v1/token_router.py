"""Token Management Router."""

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Dict, Any
import structlog

from app.domain.value_objects.email import Email
from app.domain.errors.token_errors import TokenNotFoundError, TokenExpiredError, TokenRefreshError
from app.application.usecases.get_token_usecase import GetTokenUseCase
from app.application.usecases.refresh_token_usecase import RefreshTokenUseCase
from app.application.usecases.get_token_status_usecase import GetTokenStatusUseCase

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/tokens", tags=["tokens"])


def get_get_token_usecase():
    """Get token use case dependency."""
    from app.main import container
    return container.get_get_token_usecase()


def get_refresh_token_usecase():
    """Get refresh token use case dependency."""
    from app.main import container
    return container.get_refresh_token_usecase()


def get_token_status_usecase():
    """Get token status use case dependency."""
    from app.main import container
    return container.get_token_status_usecase()


@router.get("/gmail/{email}")
async def get_token(
    email: str = Path(..., description="Email address"),
    get_token_use_case: GetTokenUseCase = Depends(get_get_token_usecase)
) -> Dict[str, Any]:
    """Get valid token for email."""
    logger.info("get_token_api_requested", email=email)
    
    try:
        # Validate email
        email_vo = Email(email)
        
        # Get token
        token_data = await get_token_use_case.execute(email_vo)
        
        logger.info("get_token_api_success", email=email)
        return {
            "email": email,
            "token": token_data,
            "status": "success"
        }
        
    except TokenNotFoundError as e:
        logger.warning("get_token_api_not_found", email=email)
        raise HTTPException(status_code=404, detail=str(e))
        
    except TokenExpiredError as e:
        logger.warning("get_token_api_expired", email=email)
        raise HTTPException(status_code=410, detail=str(e))
        
    except Exception as e:
        logger.error("get_token_api_failed", email=email, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get token: {str(e)}")


@router.post("/gmail/{email}/refresh")
async def refresh_token(
    email: str = Path(..., description="Email address"),
    refresh_token_use_case: RefreshTokenUseCase = Depends(get_refresh_token_usecase)
) -> Dict[str, Any]:
    """Refresh token for email."""
    logger.info("refresh_token_api_requested", email=email)
    
    try:
        # Validate email
        email_vo = Email(email)
        
        # Refresh token
        token_data = await refresh_token_use_case.execute(email_vo)
        
        logger.info("refresh_token_api_success", email=email)
        return {
            "email": email,
            "token": token_data,
            "status": "refreshed"
        }
        
    except TokenNotFoundError as e:
        logger.warning("refresh_token_api_not_found", email=email)
        raise HTTPException(status_code=404, detail=str(e))
        
    except TokenRefreshError as e:
        logger.error("refresh_token_api_failed", email=email, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error("refresh_token_api_error", email=email, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to refresh token: {str(e)}")


@router.get("/gmail/{email}/status")
async def get_token_status(
    email: str = Path(..., description="Email address"),
    get_token_status_use_case: GetTokenStatusUseCase = Depends(get_token_status_usecase)
) -> Dict[str, Any]:
    """Get token status for email."""
    logger.info("get_token_status_api_requested", email=email)
    
    try:
        # Validate email
        email_vo = Email(email)
        
        # Get status
        status = await get_token_status_use_case.execute(email_vo)
        
        logger.info("get_token_status_api_success", email=email)
        return status
        
    except TokenNotFoundError as e:
        logger.warning("get_token_status_api_not_found", email=email)
        raise HTTPException(status_code=404, detail=str(e))
        
    except Exception as e:
        logger.error("get_token_status_api_failed", email=email, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get token status: {str(e)}")
