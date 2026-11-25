"""
Platform-wide custom exceptions.
"""


class TenantNotFoundError(Exception):
    """Raised when a request cannot be resolved to a valid school tenant."""


class TenantAccessDeniedError(PermissionError):
    """Raised when a user attempts to access a resource outside their tenant."""


class SubscriptionRequiredError(Exception):
    """Raised when a school's subscription does not cover the requested feature."""


class InvalidUsernameFormatError(ValueError):
    """Raised when a generated or supplied username does not match the platform format."""


class SeedingError(Exception):
    """Raised when school seeding (roles, classes) fails during school creation."""
