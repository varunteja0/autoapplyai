from __future__ import annotations


class AutoApplyError(Exception):
    """Base exception for AutoApplyAI."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(AutoApplyError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class AuthorizationError(AutoApplyError):
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, status_code=403)


class NotFoundError(AutoApplyError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)


class RateLimitError(AutoApplyError):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


class ValidationError(AutoApplyError):
    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=422)


class PlatformDetectionError(AutoApplyError):
    def __init__(self, url: str):
        super().__init__(f"Could not detect platform for URL: {url}", status_code=400)


class CaptchaDetectedError(AutoApplyError):
    def __init__(self, message: str = "CAPTCHA detected, manual intervention required"):
        super().__init__(message, status_code=409)


class ApplicationBotError(AutoApplyError):
    def __init__(self, message: str = "Application automation failed"):
        super().__init__(message, status_code=500)
