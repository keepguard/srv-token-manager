"""Health Check Port - Primary interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class HealthCheckPort(ABC):
    """Primary port for health check operations."""
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Check service health."""
        pass
    
    @abstractmethod
    async def check_token_health(self) -> Dict[str, Any]:
        """Check token health."""
        pass
