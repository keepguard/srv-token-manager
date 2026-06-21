"""Validation errors for domain objects."""


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


class EmailValidationError(ValidationError):
    """Raised when email validation fails."""
    pass


class TokenExpiryValidationError(ValidationError):
    """Raised when token expiry validation fails."""
    pass


class RefreshStrategyValidationError(ValidationError):
    """Raised when refresh strategy validation fails."""
    pass
