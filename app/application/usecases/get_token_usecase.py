"""Get Token Use Case."""

import structlog
from typing import Dict, Any, Optional

from app.domain.value_objects.email import Email
from app.domain.entities.token import Token
from app.domain.errors.token_errors import TokenNotFoundError, TokenExpiredError
from app.application.ports.outbound.cache_port import CachePort
from app.application.ports.outbound.token_repository_port import TokenRepositoryPort
from app.application.ports.outbound.oauth2_client_port import OAuth2ClientPort

logger = structlog.get_logger()


class GetTokenUseCase:
    """Use case for getting valid token."""
    
    def __init__(
        self,
        cache_port: CachePort,
        repository_port: TokenRepositoryPort,
        oauth2_client_port: OAuth2ClientPort
    ):
        self.cache_port = cache_port
        self.repository_port = repository_port
        self.oauth2_client_port = oauth2_client_port
    
    async def execute(self, email: Email) -> Dict[str, Any]:
        """Execute get token use case."""
        logger.info("get_token_started", email=str(email))
        
        try:
            # Try to get from cache first
            token_data = await self._get_from_cache(email)
            if token_data:
                logger.info("get_token_cache_hit", email=str(email))
                return token_data
            
            # Get from repository
            token = await self._get_from_repository(email)
            if not token:
                raise TokenNotFoundError(f"Token not found for email: {email}")
            
            # Check if token is valid
            if token.is_expired():
                logger.warning("get_token_expired", email=str(email))
                raise TokenExpiredError(f"Token expired for email: {email}")
            
            # Convert to dict and cache
            token_data = token.to_dict()
            await self._cache_token(email, token_data)
            
            logger.info("get_token_success", email=str(email), expires_in_minutes=token.minutes_until_expiry())
            return token_data
            
        except Exception as e:
            logger.error("get_token_failed", email=str(email), error=str(e))
            raise
    
    async def _get_from_cache(self, email: Email) -> Optional[Dict[str, Any]]:
        """Get token from cache."""
        cache_key = f"token:{email}"
        return await self.cache_port.get(cache_key)
    
    async def _get_from_repository(self, email: Email) -> Optional[Token]:
        """Get token from repository."""
        return await self.repository_port.get(email)
    
    async def _cache_token(self, email: Email, token_data: Dict[str, Any]) -> None:
        """Cache token data."""
        cache_key = f"token:{email}"
        # Cache for 55 minutes (3300 seconds)
        await self.cache_port.set(cache_key, token_data, ttl=3300)
