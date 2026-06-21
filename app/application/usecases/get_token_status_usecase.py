"""Get Token Status Use Case."""

import structlog
from typing import Dict, Any, Optional

from app.domain.value_objects.email import Email
from app.domain.entities.token import Token
from app.domain.errors.token_errors import TokenNotFoundError
from app.application.ports.outbound.token_repository_port import TokenRepositoryPort
from app.application.ports.outbound.cache_port import CachePort

logger = structlog.get_logger()


class GetTokenStatusUseCase:
    """Use case for getting token status."""
    
    def __init__(
        self, 
        repository_port: TokenRepositoryPort,
        cache_port: CachePort
    ):
        self.repository_port = repository_port
        self.cache_port = cache_port
    
    async def execute(self, email: Email) -> Dict[str, Any]:
        """Execute get token status use case."""
        logger.info("get_token_status_started", email=str(email))
        
        try:
            # Try to get from cache first
            token_data = await self._get_from_cache(email)
            if token_data:
                # Create token from cached data
                token = Token.from_dict(email, token_data)
            else:
                # Get token from repository
                token = await self.repository_port.get(email)
                if not token:
                    raise TokenNotFoundError(f"Token not found for email: {email}")
            
            # Build status response
            status = {
                "email": str(email),
                "is_valid": token.is_valid(),
                "is_expired": token.is_expired(),
                "expires_in_seconds": token.seconds_until_expiry(),
                "expires_in_minutes": token.minutes_until_expiry(),
                "needs_refresh": token.needs_refresh(),
                "refresh_count": token.refresh_count,
                "last_refresh": token.last_refresh.isoformat() + 'Z' if token.last_refresh else None,
                "expiry": token.expiry.to_iso_string()
            }
            
            logger.info("get_token_status_success", email=str(email), status=status)
            return status
            
        except Exception as e:
            logger.error("get_token_status_failed", email=str(email), error=str(e))
            raise
    
    async def _get_from_cache(self, email: Email) -> Optional[Dict[str, Any]]:
        """Get token from cache."""
        cache_key = f"token:{email}"
        return await self.cache_port.get(cache_key)
