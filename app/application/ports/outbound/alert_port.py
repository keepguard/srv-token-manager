"""Alert Port - Secondary interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class AlertPort(ABC):
    """Secondary port for alert operations."""
    
    @abstractmethod
    async def send_alert(self, message: str, level: str = "warning", metadata: Dict[str, Any] = None) -> None:
        """Send alert."""
        pass
    
    @abstractmethod
    async def send_critical_alert(self, message: str, metadata: Dict[str, Any] = None) -> None:
        """Send critical alert."""
        pass
