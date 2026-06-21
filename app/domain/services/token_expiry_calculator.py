"""Token Expiry Calculator Domain Service."""

from datetime import datetime, timedelta
from typing import Optional

from app.domain.value_objects.token_expiry import TokenExpiry


class TokenExpiryCalculator:
    """Domain service for calculating token expiry times."""
    
    @staticmethod
    def calculate_refresh_time(expiry: TokenExpiry, minutes_before: int = 5) -> datetime:
        """Calculate when token should be refreshed."""
        return expiry.value - timedelta(minutes=minutes_before)
    
    @staticmethod
    def is_time_for_refresh(expiry: TokenExpiry, minutes_before: int = 5) -> bool:
        """Check if it's time to refresh token."""
        return expiry.needs_refresh(minutes_before)
    
    @staticmethod
    def calculate_cache_ttl(expiry: TokenExpiry, buffer_minutes: int = 5) -> int:
        """Calculate cache TTL in seconds."""
        seconds_until_expiry = expiry.seconds_until_expiry()
        buffer_seconds = buffer_minutes * 60
        return max(0, seconds_until_expiry - buffer_seconds)
    
    @staticmethod
    def get_next_refresh_time(expiry: TokenExpiry, minutes_before: int = 5) -> Optional[datetime]:
        """Get next refresh time if token needs refresh."""
        if TokenExpiryCalculator.is_time_for_refresh(expiry, minutes_before):
            return TokenExpiryCalculator.calculate_refresh_time(expiry, minutes_before)
        return None
