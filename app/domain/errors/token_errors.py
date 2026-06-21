"""Token domain errors."""


class TokenError(Exception):
    """Base exception for token-related errors."""
    pass


class TokenExpiredError(TokenError):
    """Raised when token is expired."""
    pass


class TokenInvalidError(TokenError):
    """Raised when token is invalid."""
    pass


class TokenNotFoundError(TokenError):
    """Raised when token is not found."""
    pass


class TokenRefreshError(TokenError):
    """Raised when token refresh fails."""
    pass


class TokenValidationError(TokenError):
    """Raised when token validation fails."""
    pass
