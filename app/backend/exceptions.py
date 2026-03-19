"""Custom exceptions for the SadTalker Runpod worker."""


class ConfigurationError(RuntimeError):
    """Raised when the SadTalker runtime is not configured correctly."""


class GenerationError(RuntimeError):
    """Raised when SadTalker fails to generate an output video."""

    def __init__(self, message: str, logs: str = "") -> None:
        super().__init__(message)
        self.logs = logs
