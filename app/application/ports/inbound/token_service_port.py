"""Token Service Port - Primary interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from app.domain.value_objects.email import Email
from app.domain.entities.token import Token


class TokenServicePort(ABC):
    """Primary port for token management operations."""
    
    @abstractmethod
    async def get_token(self, email: Email) -> Dict[str, Any]:
        """Get valid token for email."""
        pass
    
    @abstractmethod
    async def refresh_token(self, email: Email) -> Dict[str, Any]:
        """Refresh token for email."""
        pass
    
    @abstractmethod
    async def get_token_status(self, email: Email) -> Dict[str, Any]:
        """Get token status for email."""
        pass
    
    @abstractmethod
    async def store_token(self, token: Token) -> None:
        """Store token."""
        pass
