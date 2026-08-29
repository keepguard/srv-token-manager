"""Refresh Token Use Case."""

import structlog
from typing import Dict, Any, Optional

from app.domain.value_objects.email import Email
from app.domain.entities.token import Token
from app.domain.value_objects.token_expiry import TokenExpiry
from app.domain.errors.token_errors import TokenNotFoundError, TokenRefreshError
from app.application.ports.outbound.cache_port import CachePort
from app.application.ports.outbound.token_repository_port import TokenRepositoryPort
from app.application.ports.outbound.oauth2_client_port import OAuth2ClientPort
from app.application.ports.outbound.alert_port import AlertPort
from app.infrastructure.audit_publisher import AuditEventPublisher

logger = structlog.get_logger()


class RefreshTokenUseCase:
    """Use case for refreshing token."""
    
    def __init__(
        self,
        cache_port: CachePort,
        repository_port: TokenRepositoryPort,
        oauth2_client_port: OAuth2ClientPort,
        alert_port: AlertPort,
        audit_publisher: Optional[AuditEventPublisher] = None,
    ):
        self.cache_port = cache_port
        self.repository_port = repository_port
        self.oauth2_client_port = oauth2_client_port
        self.alert_port = alert_port
        self.audit_publisher = audit_publisher
    
    async def execute(self, email: Email) -> Dict[str, Any]:
        """Execute refresh token use case."""
        logger.info("refresh_token_started", email=str(email))
        
        try:
            # Try to get from cache first
            token_data = await self._get_from_cache(email)
            if token_data:
                # Create token from cached data
                token = Token.from_dict(email, token_data)
            else:
                # Get current token from repository
                token = await self.repository_port.get(email)
                if not token:
                    raise TokenNotFoundError(f"Token not found for email: {email}")
            
            # Refresh token using OAuth2 client
            new_token_data = await self.oauth2_client_port.refresh_token(token.to_dict())
            
            # Create new expiry
            new_expiry = TokenExpiry.from_iso_string(new_token_data["expiry"])
            
            # Update token
            token.refresh(new_token_data["access_token"], new_expiry)
            
            # Save updated token
            await self.repository_port.save(token)
            
            # Update cache
            await self._update_cache(email, token)
            
            logger.info(
                "refresh_token_success",
                email=str(email),
                new_expiry=new_expiry.to_iso_string(),
                refresh_count=token.refresh_count
            )

            return token.to_dict()
            
        except Exception as e:
            logger.error("refresh_token_failed", email=str(email), error=str(e))
            if self.audit_publisher:
                self.audit_publisher.publish(
                    "TOKEN_REFRESH_FAILURE",
                    "FAILURE",
                    None,
                    "TOKEN",
                    self._mask_email(str(email)),
                )
            
            # Send alert for refresh failure
            await self.alert_port.send_critical_alert(
                f"Token refresh failed for {email}: {str(e)}",
                metadata={"email": str(email), "error": str(e)}
            )
            
            raise TokenRefreshError(f"Failed to refresh token for {email}: {str(e)}") from e

    def _mask_email(self, email: str) -> str:
        at = email.find("@")
        if at <= 0:
            return "***"
        local = email[:at]
        if len(local) <= 2:
            return "***" + email[at:]
        return local[:1] + "***" + email[at:]

    async def _get_from_cache(self, email: Email) -> Optional[Dict[str, Any]]:
        """Get token from cache."""
        if not self.cache_port:
            return None
        cache_key = f"token:{email}"
        return await self.cache_port.get(cache_key)
    
    async def _update_cache(self, email: Email, token: Token) -> None:
        """Update token in cache."""
        if not self.cache_port:
            return
        cache_key = f"token:{email}"
        token_data = token.to_dict()
        # Cache for 55 minutes (3300 seconds)
        await self.cache_port.set(cache_key, token_data, ttl=3300)
