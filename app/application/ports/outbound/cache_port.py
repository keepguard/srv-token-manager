"""Cache Port - Secondary interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class CachePort(ABC):
    """Secondary port for cache operations."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> bool:
        """Set value in cache with TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
