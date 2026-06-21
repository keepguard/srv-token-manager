"""Token Repository Port - Secondary interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from app.domain.value_objects.email import Email
from app.domain.entities.token import Token


class TokenRepositoryPort(ABC):
    """Secondary port for token persistence operations."""
    
    @abstractmethod
    async def get(self, email: Email) -> Optional[Token]:
        """Get token by email."""
        pass
    
    @abstractmethod
    async def save(self, token: Token) -> None:
        """Save token."""
        pass
    
    @abstractmethod
    async def delete(self, email: Email) -> bool:
        """Delete token by email."""
        pass
    
    @abstractmethod
    async def exists(self, email: Email) -> bool:
        """Check if token exists."""
        pass
    
    @abstractmethod
    async def get_all(self) -> list[Token]:
        """Get all tokens."""
        pass
