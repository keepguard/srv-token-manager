"""Token Expiry Value Object for domain validation."""

from datetime import datetime, timedelta, timezone
from typing import Any
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenExpiry:
    """Token Expiry Value Object with validation."""
    
    value: datetime
    
    def __post_init__(self) -> None:
        """Validate expiry date."""
        # Allow expired tokens to be loaded (for refresh purposes)
        # Validation of expiry happens at use-time, not load-time
        pass
    
    @classmethod
    def from_iso_string(cls, iso_string: str) -> "TokenExpiry":
        """Create from ISO string."""
        try:
            # Handle both 'Z' and '+00:00' formats
            if iso_string.endswith('Z'):
                dt = datetime.fromisoformat(iso_string[:-1] + '+00:00')
            elif '+' in iso_string or iso_string.count('-') > 2:
                # Already has timezone info
                dt = datetime.fromisoformat(iso_string)
            else:
                # Naive datetime - assume UTC
                dt = datetime.fromisoformat(iso_string).replace(tzinfo=timezone.utc)
            return cls(dt)
        except ValueError as e:
            raise ValueError(f"Invalid ISO datetime format: {iso_string}") from e
    
    @classmethod
    def from_timestamp(cls, timestamp: float) -> "TokenExpiry":
        """Create from Unix timestamp."""
        try:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return cls(dt)
        except (ValueError, OSError) as e:
            raise ValueError(f"Invalid timestamp: {timestamp}") from e
    
    @classmethod
    def now_plus_hours(cls, hours: int) -> "TokenExpiry":
        """Create expiry time from now plus hours."""
        expiry = datetime.now(timezone.utc) + timedelta(hours=hours)
        return cls(expiry)
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return self.value <= datetime.now(timezone.utc)
    
    def seconds_until_expiry(self) -> int:
        """Get seconds until expiry."""
        delta = self.value - datetime.now(timezone.utc)
        return max(0, int(delta.total_seconds()))
    
    def minutes_until_expiry(self) -> int:
        """Get minutes until expiry."""
        return self.seconds_until_expiry() // 60
    
    def needs_refresh(self, minutes_before: int = 5) -> bool:
        """Check if token needs refresh based on minutes before expiry."""
        return self.minutes_until_expiry() <= minutes_before
    
    def to_iso_string(self) -> str:
        """Convert to ISO string."""
        if self.value.tzinfo is None:
            # Naive datetime - add Z
            return self.value.isoformat() + 'Z'
        else:
            # Timezone-aware datetime - use as is
            return self.value.isoformat()
    
    def __str__(self) -> str:
        """String representation."""
        return self.to_iso_string()
    
    def __repr__(self) -> str:
        """Debug representation."""
        return f"TokenExpiry('{self.to_iso_string()}')"
    
    def __eq__(self, other: Any) -> bool:
        """Equality comparison."""
        if not isinstance(other, TokenExpiry):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        """Hash for use in sets and dicts."""
        return hash(self.value)
