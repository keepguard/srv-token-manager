"""Email Value Object for domain validation."""

import re
from typing import Any
from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    """Email Value Object with validation."""
    
    value: str
    
    def __post_init__(self) -> None:
        """Validate email format."""
        if not self._is_valid_email(self.value):
            raise ValueError(f"Invalid email format: {self.value}")
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """Check if email format is valid."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    def __repr__(self) -> str:
        """Debug representation."""
        return f"Email('{self.value}')"
    
    def __eq__(self, other: Any) -> bool:
        """Equality comparison."""
        if not isinstance(other, Email):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        """Hash for use in sets and dicts."""
        return hash(self.value)
