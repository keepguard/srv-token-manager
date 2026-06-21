"""Token Manager Client para integração com srv-email-google-sender."""

import asyncio
import httpx
import structlog
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials

logger = structlog.get_logger()


class TokenManagerClient:
    """Cliente para buscar tokens do srv-token-manager."""
    
    def __init__(
        self,
        token_manager_url: str,
        email: str,
        cache_ttl_minutes: int = 5,
        timeout_seconds: int = 10
    ):
        self.token_manager_url = token_manager_url.rstrip('/')
        self.email = email
        self.cache_ttl_minutes = cache_ttl_minutes
        self.timeout_seconds = timeout_seconds
        self._cache: Optional[Credentials] = None
        self._cache_expiry: Optional[datetime] = None
    
    async def get_credentials(self) -> Credentials:
        """Obtém credenciais do token manager com cache local."""
        logger.info("token_manager_client_get_credentials_started", email=self.email)
        
        try:
            # Verificar cache local
            if self._cache and self._cache_expiry and self._cache_expiry > datetime.utcnow():
                logger.debug("token_manager_client_cache_hit", email=self.email)
                return self._cache
            
            # Buscar do token manager
            token_data = await self._fetch_token_from_manager()
            
            # Converter para Credentials
            creds = Credentials.from_authorized_user_info(token_data)
            
            # Cache local
            self._cache = creds
            self._cache_expiry = datetime.utcnow() + timedelta(minutes=self.cache_ttl_minutes)
            
            logger.info("token_manager_client_get_credentials_success", email=self.email)
            return creds
            
        except Exception as e:
            logger.error("token_manager_client_get_credentials_failed", email=self.email, error=str(e))
            raise
    
    async def force_refresh(self) -> Credentials:
        """Força refresh do token no token manager."""
        logger.info("token_manager_client_force_refresh_started", email=self.email)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                url = f"{self.token_manager_url}/api/v1/tokens/gmail/{self.email}/refresh"
                response = await client.post(url)
                
                if response.status_code == 200:
                    refresh_data = response.json()
                    token_data = refresh_data.get("token", {})
                    
                    # Converter para Credentials
                    creds = Credentials.from_authorized_user_info(token_data)
                    
                    # Atualizar cache local
                    self._cache = creds
                    self._cache_expiry = datetime.utcnow() + timedelta(minutes=self.cache_ttl_minutes)
                    
                    logger.info("token_manager_client_force_refresh_success", email=self.email)
                    return creds
                else:
                    error_msg = f"Token refresh failed: {response.status_code} - {response.text}"
                    logger.error("token_manager_client_force_refresh_failed", email=self.email, error=error_msg)
                    raise Exception(error_msg)
                    
        except Exception as e:
            logger.error("token_manager_client_force_refresh_error", email=self.email, error=str(e))
            raise
    
    async def get_token_status(self) -> Dict[str, Any]:
        """Obtém status do token."""
        logger.info("token_manager_client_get_status_started", email=self.email)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                url = f"{self.token_manager_url}/api/v1/tokens/gmail/{self.email}/status"
                response = await client.get(url)
                
                if response.status_code == 200:
                    status = response.json()
                    logger.info("token_manager_client_get_status_success", email=self.email)
                    return status
                else:
                    error_msg = f"Status check failed: {response.status_code} - {response.text}"
                    logger.error("token_manager_client_get_status_failed", email=self.email, error=error_msg)
                    raise Exception(error_msg)
                    
        except Exception as e:
            logger.error("token_manager_client_get_status_error", email=self.email, error=str(e))
            raise
    
    async def _fetch_token_from_manager(self) -> Dict[str, Any]:
        """Busca token do token manager."""
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            url = f"{self.token_manager_url}/api/v1/tokens/gmail/{self.email}"
            response = await client.get(url)
            
            if response.status_code == 200:
                token_response = response.json()
                return token_response.get("token", {})
            elif response.status_code == 410:  # Token expired
                logger.warning("token_manager_client_token_expired", email=self.email)
                # Tentar refresh automático
                return await self._fetch_token_after_refresh()
            else:
                error_msg = f"Token fetch failed: {response.status_code} - {response.text}"
                logger.error("token_manager_client_fetch_failed", email=self.email, error=error_msg)
                raise Exception(error_msg)
    
    async def _fetch_token_after_refresh(self) -> Dict[str, Any]:
        """Busca token após refresh automático."""
        logger.info("token_manager_client_auto_refresh_started", email=self.email)
        
        try:
            # Forçar refresh
            await self.force_refresh()
            
            # Buscar token novamente
            return await self._fetch_token_from_manager()
            
        except Exception as e:
            logger.error("token_manager_client_auto_refresh_failed", email=self.email, error=str(e))
            raise
    
    def clear_cache(self) -> None:
        """Limpa cache local."""
        self._cache = None
        self._cache_expiry = None
        logger.info("token_manager_client_cache_cleared", email=self.email)
    
    def is_cache_valid(self) -> bool:
        """Verifica se cache local é válido."""
        return (
            self._cache is not None and
            self._cache_expiry is not None and
            self._cache_expiry > datetime.utcnow()
        )
