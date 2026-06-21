"""OAuth2 Client Port - Secondary interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class OAuth2ClientPort(ABC):
    """Secondary port for OAuth2 operations."""
    
    @abstractmethod
    async def refresh_token(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh OAuth2 token."""
        pass
    
    @abstractmethod
    async def validate_token(self, token_data: Dict[str, Any]) -> bool:
        """Validate OAuth2 token."""
        pass
    
    @abstractmethod
    async def get_token_info(self, token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get token information."""
        pass
