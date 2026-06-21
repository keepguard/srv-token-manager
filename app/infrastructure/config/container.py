"""Dependency Injection Container."""

from typing import Dict, Any
import structlog

from app.infrastructure.config.settings import Settings
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.oauth2.google_oauth2_client import GoogleOAuth2Client
from app.infrastructure.repository.token_repository import TokenRepository
from app.infrastructure.alerts.webhook_alert import WebhookAlert
from app.infrastructure.jobs.token_refresh_job import TokenRefreshJob
# Leader election removido para simplificar implementação local
from app.application.usecases.get_token_usecase import GetTokenUseCase
from app.application.usecases.refresh_token_usecase import RefreshTokenUseCase
from app.application.usecases.get_token_status_usecase import GetTokenStatusUseCase
from app.application.usecases.token_health_check_usecase import TokenHealthCheckUseCase

logger = structlog.get_logger()


class Container:
    """Dependency injection container."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._instances: Dict[str, Any] = {}
    
    def get_redis_cache(self) -> RedisCache:
        """Get Redis cache instance."""
        if "redis_cache" not in self._instances:
            self._instances["redis_cache"] = RedisCache(
                host=self.settings.redis.host,
                port=self.settings.redis.port,
                password=self.settings.redis.password,
                db=self.settings.redis.db,
                key_prefix=self.settings.redis.key_prefix,
                max_connections=self.settings.redis.max_connections,
                socket_timeout=self.settings.redis.socket_timeout,
                retry_on_timeout=self.settings.redis.retry_on_timeout,
                mode=getattr(self.settings.redis, 'mode', 'standalone'),
                cluster_nodes=getattr(self.settings.redis, 'cluster_nodes', None)
            )
        return self._instances["redis_cache"]
    
    def get_oauth2_client(self) -> GoogleOAuth2Client:
        """Get OAuth2 client instance."""
        if "oauth2_client" not in self._instances:
            self._instances["oauth2_client"] = GoogleOAuth2Client(
                client_secrets_file=self.settings.gmail.client_secrets_file
            )
        return self._instances["oauth2_client"]
    
    def get_token_repository(self) -> TokenRepository:
        """Get token repository instance."""
        if "token_repository" not in self._instances:
            self._instances["token_repository"] = TokenRepository(
                token_file=self.settings.gmail.token_file
            )
        return self._instances["token_repository"]
    
    def get_alert_port(self) -> WebhookAlert:
        """Get alert port instance."""
        if "alert_port" not in self._instances:
            self._instances["alert_port"] = WebhookAlert(
                webhook_url=self.settings.monitoring.alert_webhook_url
            )
        return self._instances["alert_port"]
    
    def get_get_token_usecase(self) -> GetTokenUseCase:
        """Get token use case instance."""
        if "get_token_usecase" not in self._instances:
            self._instances["get_token_usecase"] = GetTokenUseCase(
                cache_port=self.get_redis_cache(),
                repository_port=self.get_token_repository(),
                oauth2_client_port=self.get_oauth2_client()
            )
        return self._instances["get_token_usecase"]
    
    def get_refresh_token_usecase(self) -> RefreshTokenUseCase:
        """Get refresh token use case instance."""
        if "refresh_token_usecase" not in self._instances:
            self._instances["refresh_token_usecase"] = RefreshTokenUseCase(
                cache_port=self.get_redis_cache(),
                repository_port=self.get_token_repository(),
                oauth2_client_port=self.get_oauth2_client(),
                alert_port=self.get_alert_port()
            )
        return self._instances["refresh_token_usecase"]
    
    def get_token_status_usecase(self) -> GetTokenStatusUseCase:
        """Get token status use case instance."""
        if "token_status_usecase" not in self._instances:
            self._instances["token_status_usecase"] = GetTokenStatusUseCase(
                repository_port=self.get_token_repository(),
                cache_port=self.get_redis_cache()
            )
        return self._instances["token_status_usecase"]
    
    def get_token_health_check_usecase(self) -> TokenHealthCheckUseCase:
        """Get token health check use case instance."""
        if "token_health_check_usecase" not in self._instances:
            self._instances["token_health_check_usecase"] = TokenHealthCheckUseCase(
                repository_port=self.get_token_repository()
            )
        return self._instances["token_health_check_usecase"]
    
    def get_token_refresh_job(self) -> TokenRefreshJob:
        """Get token refresh job instance."""
        if "token_refresh_job" not in self._instances:
            self._instances["token_refresh_job"] = TokenRefreshJob(
                repository_port=self.get_token_repository(),
                oauth2_client_port=self.get_oauth2_client(),
                alert_port=self.get_alert_port(),
                refresh_before_minutes=self.settings.token_manager.refresh_before_expiry_minutes,
                check_interval_seconds=self.settings.monitoring.check_interval_seconds
            )
        return self._instances["token_refresh_job"]
    
    
    async def startup(self) -> None:
        """Startup dependencies."""
        logger.info("container_startup_started")
        
        try:
            # Connect Redis
            await self.get_redis_cache().connect()
            
            # Start background jobs
            await self.get_token_refresh_job().start()
            
            logger.info("container_startup_success")
            
        except Exception as e:
            logger.error("container_startup_failed", error=str(e))
            raise
    
    async def shutdown(self) -> None:
        """Shutdown dependencies."""
        logger.info("container_shutdown_started")
        
        try:
            # Stop background jobs
            await self.get_token_refresh_job().stop()
            
            # Disconnect Redis
            await self.get_redis_cache().disconnect()
            
            logger.info("container_shutdown_success")
            
        except Exception as e:
            logger.error("container_shutdown_failed", error=str(e))
            raise
