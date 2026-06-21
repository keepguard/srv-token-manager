"""Token Refresh Background Job."""

import asyncio
import structlog
from typing import List
from datetime import datetime, timedelta

from app.domain.value_objects.email import Email
from app.domain.entities.token import Token
from app.domain.errors.token_errors import TokenRefreshError
from app.application.ports.outbound.token_repository_port import TokenRepositoryPort
from app.application.ports.outbound.oauth2_client_port import OAuth2ClientPort
from app.application.ports.outbound.alert_port import AlertPort
from app.application.usecases.refresh_token_usecase import RefreshTokenUseCase
from app.infrastructure.monitoring.metrics import increment_token_refresh, update_token_expiry

logger = structlog.get_logger()


class TokenRefreshJob:
    """Background job for proactive token refresh."""
    
    def __init__(
        self,
        repository_port: TokenRepositoryPort,
        oauth2_client_port: OAuth2ClientPort,
        alert_port: AlertPort,
        refresh_before_minutes: int = 5,
        check_interval_seconds: int = 60
    ):
        self.repository_port = repository_port
        self.oauth2_client_port = oauth2_client_port
        self.alert_port = alert_port
        self.refresh_before_minutes = refresh_before_minutes
        self.check_interval_seconds = check_interval_seconds
        self.is_running = False
        self._task = None
    
    async def start(self) -> None:
        """Start the background job."""
        if self.is_running:
            logger.warning("token_refresh_job_already_running")
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._run())
        logger.info("token_refresh_job_started", check_interval=self.check_interval_seconds)
    
    async def stop(self) -> None:
        """Stop the background job."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("token_refresh_job_stopped")
    
    async def _run(self) -> None:
        """Main job loop."""
        while self.is_running:
            try:
                await self._check_and_refresh_tokens()
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("token_refresh_job_error", error=str(e))
                await asyncio.sleep(self.check_interval_seconds)
    
    async def _check_and_refresh_tokens(self) -> None:
        """Check all tokens and refresh if needed."""
        logger.info("token_refresh_check_started")
        
        try:
            # Get all tokens
            tokens = await self.repository_port.get_all()
            
            if not tokens:
                logger.info("token_refresh_check_no_tokens")
                return
            
            # Check each token
            for token in tokens:
                await self._check_token(token)
            
            logger.info("token_refresh_check_completed", total_tokens=len(tokens))
            
        except Exception as e:
            logger.error("token_refresh_check_failed", error=str(e))
    
    async def _check_token(self, token: Token) -> None:
        """Check individual token and refresh if needed."""
        try:
            # Update metrics
            update_token_expiry(str(token.email), token.seconds_until_expiry())
            
            # Check if token needs refresh
            if not token.needs_refresh(self.refresh_before_minutes):
                logger.debug("token_no_refresh_needed", email=str(token.email))
                return
            
            logger.info("token_refresh_needed", email=str(token.email))
            
            # Create refresh use case
            refresh_use_case = RefreshTokenUseCase(
                cache_port=None,  # Will be injected by DI
                repository_port=self.repository_port,
                oauth2_client_port=self.oauth2_client_port,
                alert_port=self.alert_port
            )
            
            # Refresh token
            await refresh_use_case.execute(token.email)
            
            # Update metrics
            increment_token_refresh(str(token.email), "success", "proactive")
            
            logger.info("token_refresh_success", email=str(token.email))
            
        except TokenRefreshError as e:
            logger.error("token_refresh_failed", email=str(token.email), error=str(e))
            increment_token_refresh(str(token.email), "failure", "proactive")
            
            # Send alert
            await self.alert_port.send_critical_alert(
                f"Token refresh failed for {token.email}: {str(e)}",
                metadata={"email": str(token.email), "error": str(e)}
            )
            
        except Exception as e:
            logger.error("token_check_error", email=str(token.email), error=str(e))
            increment_token_refresh(str(token.email), "error", "proactive")
