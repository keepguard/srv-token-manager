"""Refresh Strategy Enum for domain logic."""

from enum import Enum


class RefreshStrategy(Enum):
    """Refresh strategy enumeration."""
    
    PROACTIVE = "proactive"
    REACTIVE = "reactive"
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> "RefreshStrategy":
        """Create from string value."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Invalid refresh strategy: {value}. Must be one of: {[s.value for s in cls]}")
    
    def is_proactive(self) -> bool:
        """Check if strategy is proactive."""
        return self == RefreshStrategy.PROACTIVE
    
    def is_reactive(self) -> bool:
        """Check if strategy is reactive."""
        return self == RefreshStrategy.REACTIVE
