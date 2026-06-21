"""Token Entity - Aggregate Root."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from app.domain.value_objects.email import Email
from app.domain.value_objects.token_expiry import TokenExpiry
from app.domain.errors.token_errors import TokenExpiredError, TokenInvalidError


@dataclass
class Token:
    """Token Entity - Aggregate Root for token management."""
    
    email: Email
    access_token: str
    refresh_token: str
    expiry: TokenExpiry
    token_uri: str
    client_id: str
    client_secret: str
    scopes: list[str]
    last_refresh: Optional[datetime] = None
    refresh_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate token after initialization."""
        self._validate_token()
    
    def _validate_token(self) -> None:
        """Validate token data."""
        if not self.access_token:
            raise TokenInvalidError("Access token cannot be empty")
        
        if not self.refresh_token:
            raise TokenInvalidError("Refresh token cannot be empty")
        
        if not self.token_uri:
            raise TokenInvalidError("Token URI cannot be empty")
        
        if not self.client_id:
            raise TokenInvalidError("Client ID cannot be empty")
        
        if not self.client_secret:
            raise TokenInvalidError("Client secret cannot be empty")
        
        if not self.scopes:
            raise TokenInvalidError("Scopes cannot be empty")
    
    def is_valid(self) -> bool:
        """Check if token is valid."""
        return not self.expiry.is_expired()
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return self.expiry.is_expired()
    
    def needs_refresh(self, minutes_before: int = 5) -> bool:
        """Check if token needs refresh."""
        return self.expiry.needs_refresh(minutes_before)
    
    def seconds_until_expiry(self) -> int:
        """Get seconds until expiry."""
        return self.expiry.seconds_until_expiry()
    
    def minutes_until_expiry(self) -> int:
        """Get minutes until expiry."""
        return self.expiry.minutes_until_expiry()
    
    def refresh(self, new_access_token: str, new_expiry: TokenExpiry) -> None:
        """Refresh token with new access token and expiry."""
        # Expired tokens CAN and SHOULD be refreshed using refresh_token
        # The validation should be on the refresh_token, not the access_token expiry
        
        self.access_token = new_access_token
        self.expiry = new_expiry
        self.last_refresh = datetime.now(timezone.utc)
        self.refresh_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary."""
        return {
            "token": self.access_token,  # Google Credentials espera 'token' não 'access_token'
            "refresh_token": self.refresh_token,
            "token_uri": self.token_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scopes": self.scopes,
            # Campos extras para compatibilidade
            "access_token": self.access_token,  # Manter para retrocompatibilidade
            "expiry": self.expiry.to_iso_string().replace('+00:00', 'Z') if '+00:00' in self.expiry.to_iso_string() else self.expiry.to_iso_string(),
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
            "refresh_count": self.refresh_count,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, email: Email, data: Dict[str, Any]) -> "Token":
        """Create token from dictionary."""
        # Handle both 'token' and 'access_token' keys (Google API compatibility)
        access_token = data.get("access_token") or data.get("token")
        
        return cls(
            email=email,
            access_token=access_token,
            refresh_token=data["refresh_token"],
            expiry=TokenExpiry.from_iso_string(data["expiry"]),
            token_uri=data["token_uri"],
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            scopes=data["scopes"],
            last_refresh=datetime.fromisoformat(data["last_refresh"].replace('Z', '').replace('+00:00', '')) if data.get("last_refresh") else None,
            refresh_count=data.get("refresh_count", 0),
            metadata=data.get("metadata", {})
        )
    
    def __str__(self) -> str:
        """String representation."""
        return f"Token(email={self.email}, expires_in={self.minutes_until_expiry()}min)"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return f"Token(email={self.email!r}, expiry={self.expiry!r}, refresh_count={self.refresh_count})"
