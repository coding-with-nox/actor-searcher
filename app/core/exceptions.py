class AppError(Exception):
    """Base application exception."""


class RetryableProviderError(AppError):
    """External provider transient failure."""


class NonRetryableProviderError(AppError):
    """External provider permanent failure."""
