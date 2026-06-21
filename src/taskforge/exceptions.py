class ValidationError(Exception):
    """Raised when user input validation fails."""
    pass


class LLMOutputError(Exception):
    """Raised when an LLM returns invalid, malformed, or unusable output.
    These errors are eligible for retry by the tenacity retry decorator.
    """
    pass
